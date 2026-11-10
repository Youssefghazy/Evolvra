"""Rubric judging by an ensemble of free-tier models.

Each judge returns strict JSON. Per-metric medians across judges become the 'ensemble'
scores; disagreements are kept (every judge's row is stored) so bias is inspectable.
Every call goes through the router: quota-guarded and cached, so re-scoring is free.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import statistics
from collections import Counter
from dataclasses import dataclass

from ..router import client, quota
from . import checks

# Three free models, three lineages, three providers (OpenAI on Groq, NVIDIA on OpenRouter, Google on Gemini).
# Gemma was dropped 2026-11-03 (failed most calls, 1.0 on the rest). Qwen was replaced 2026-11-05: reliable when it
# had budget, but it shared Groq's 200k tokens/day with gpt-oss and starved on busy days. Override: EVOLVRA_JUDGES.
DEFAULT_JUDGES: tuple[tuple[str, str], ...] = (
    ("groq", "openai/gpt-oss-120b"),
    ("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free"),
    ("gemini", "gemini-3.5-flash-lite"),
)
# Qwen on Groq is capped at 1,000 output tokens/minute and spends 1-2k on hidden reasoning per verdict.
# Ask it not to reason; if the provider rejects the value, the router remembers and retries without it.
JUDGE_REASONING: dict[str, str | None] = {"qwen/qwen3.8-27b": "none"}
RUBRIC = ("correctness", "completeness", "quality", "evidence")
QA_AGENTS = {"evidence-collector", "reality-checker"}   # their deliverable is findings backed by proof
MAX_TOKENS = 900
# Qwen on Groq can spend all 900 tokens on hidden reasoning and return empty content.
RETRY_MAX_TOKENS = 2400
# OpenRouter's free tier is capped by requests per day (40), not tokens. Nemotron was cut off at 900 tokens
# often enough to average ~2 requests per verdict (round 6), so it gets the large budget on the first try.
JUDGE_MAX_TOKENS: dict[str, int] = {"nvidia/nemotron-3-ultra-550b-a55b:free": RETRY_MAX_TOKENS}

SYSTEM = (
    "You are a strict, fair QA reviewer for an AI agency. You grade one agent's work on one task. "
    "Judge only what is shown. Unverifiable claims count against the work. "
    "Reply with a single JSON object and nothing else."
)

PROMPT = """# Mission brief
{brief}

# Agent
{agent} (role description: {agent_description})

# Task
{task}

# Acceptance criteria (grade each one by its id, exactly as written)
{criteria}

# Attempts: {attempts}   Final verdict recorded by the orchestrator: {verdict}
# Agent's own evidence statement
{evidence}

# Output files
{output}
{facts}
# Calibration (apply strictly)
- 1.0 means flawless AND every claim is verifiable from what is shown. Reserve it.
- Typical competent work scores 0.6-0.8. Minor gaps: 0.8-0.9.
- Any invented measurement, command output or file content caps `evidence` at 0.2 and `correctness` at 0.5.
- A missing required element (an acceptance criterion not addressed) caps `completeness` at 0.5.
- Honestly stating what could not be verified is NOT a flaw; pretending to have verified it is.

# Reading the criteria (apply literally)
- Grade every criterion by its id (C1, C2, ...), one entry per id, in order. Do not restate, merge, split or
  narrow a criterion. Its scope is exactly its words: "the text names exactly two features" is about the whole
  text, not each paragraph. Mark it unmet only when the shown work contradicts what the words say.

# Grade
Return JSON with exactly these keys:
{{
  "acceptance": [{{"id": "C1", "met": true|false, "reason": "<short>"}}],
  "correctness": <0..1, acceptance criteria actually met>,
  "completeness": <0..1, nothing required is missing>,
  "quality": <0..1, craftsmanship of the deliverable>,
  "evidence": <0..1, how well the evidence proves the claims>,
  "critique": "<one sentence, the most important problem or 'none'>",
  "failure_class": "<snake_case label of the main failure, or 'none'>"
}}"""


@dataclass
class JudgeResult:
    judge: str                     # provider/model
    scores: dict[str, float]
    acceptance: list[dict]
    critique: str
    failure_class: str
    cached: bool
    raw_text: str


def judges_from_env() -> list[tuple[str, str]]:
    """EVOLVRA_JUDGES="groq:openai/gpt-oss-120b,gemini:gemma-4-31b-it" overrides the default set."""
    spec = os.environ.get("EVOLVRA_JUDGES")
    if not spec:
        return list(DEFAULT_JUDGES)
    out = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        provider, _, model = item.partition(":")
        out.append((provider.strip(), model.strip() or client.default_model(provider.strip())))
    return out


FACTS_HEADER = ("\n# Measured facts (computed by a program; trust these over your own counting and never report "
                "a count violation that contradicts them)\n")


def render_prompt(*, brief: str, agent: str, agent_description: str, task: str, criteria: list[str],
                  attempts: int, verdict: str | None, evidence: str | None, output: str | None,
                  facts: str = "") -> str:
    return PROMPT.format(
        facts=(FACTS_HEADER + facts + "\n") if facts else "",
        brief=brief,
        agent=agent,
        agent_description=agent_description or "(unknown)",
        task=task,
        criteria="\n".join(f"C{i}. {c}" for i, c in enumerate(criteria, 1)) or "- (none given)",
        attempts=attempts,
        verdict=verdict or "none",
        evidence=(evidence or "(no evidence statement)").strip(),
        output=output or "(no output files found)",
    )


def build_prompt(task: sqlite3.Row, brief: str, agent_description: str) -> str:
    attempts = json.loads(task["attempts_json"] or "[]")
    last = attempts[-1] if attempts else {}
    criteria = json.loads(task["acceptance_json"] or "[]")
    return render_prompt(
        brief=brief, agent=task["agent_slug"], agent_description=agent_description, task=task["task"],
        criteria=criteria, attempts=task["attempts"],
        verdict=task["verdict"], evidence=last.get("evidence"),
        output=checks.read_output(task["output_dir"],
                                  mentions="\n".join([last.get("evidence") or "", task["task"] or "", *criteria]),
                                  qa=task["agent_slug"] in QA_AGENTS),
        facts=checks.measured_facts(task["output_dir"], criteria),
    )


def parse_judge_json(text: str) -> dict | None:
    """Tolerate code fences and chatter: take the first {...} block that parses."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start = cleaned.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[start:i + 1])
                    except json.JSONDecodeError:
                        break
        start = cleaned.find("{", start + 1)
    return None


def parse_verdict(text: str) -> dict | None:
    """A judge verdict must carry the rubric scores. A reply cut off mid-JSON still holds a complete
    inner object (one acceptance item); reading that as the verdict scored every metric 0.0."""
    data = parse_judge_json(text)
    return data if data and all(k in data for k in RUBRIC) else None


def _clamp(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def judge_task(conn: sqlite3.Connection, task: sqlite3.Row, brief: str, agent_description: str,
               judges: list[tuple[str, str]] | None = None, *, _transport=None) -> list[JudgeResult]:
    criteria = json.loads(task["acceptance_json"] or "[]")
    return judge_prompt(conn, build_prompt(task, brief, agent_description), judges, criteria=criteria,
                        _transport=_transport)


def normalize_acceptance(items, criteria: list[str]) -> list[dict]:
    """Map a judge's acceptance entries back to the criteria as written. Entries answer by id ("C2"), by
    index, or (older prompt) by quoting the text. Anything that matches no criterion verbatim is kept but
    marked `rewritten`: on 2026-11-05 a judge narrowed "the text names exactly two product features" to
    "each paragraph names...", failed it, and that misread became the agent's top failure class."""
    if not isinstance(items, list):
        return []
    canon = {c.strip().lower(): i for i, c in enumerate(criteria)}
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        idx = None
        ref = it.get("id", it.get("index"))
        if ref is not None:
            m = re.fullmatch(r"\s*[Cc]?(\d+)\s*", str(ref))
            if m and 1 <= int(m.group(1)) <= len(criteria):
                idx = int(m.group(1)) - 1
        if idx is None and isinstance(it.get("criterion"), str):
            idx = canon.get(it["criterion"].strip().lower())
        entry = {"met": it.get("met"), "reason": str(it.get("reason") or "")}
        if idx is not None:
            entry.update(id=f"C{idx + 1}", criterion=criteria[idx])
        else:
            entry.update(criterion=str(it.get("criterion") or ref or ""), rewritten=True)
        out.append(entry)
    return out


def judge_prompt(conn: sqlite3.Connection, prompt: str, judges: list[tuple[str, str]] | None = None, *,
                 criteria: list[str] | None = None, _transport=None) -> list[JudgeResult]:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    results: list[JudgeResult] = []
    for provider, model in judges or judges_from_env():
        name = f"{provider}/{model}"
        try:
            effort = JUDGE_REASONING.get(model, client.DEFAULT_REASONING_EFFORT)
            first = JUDGE_MAX_TOKENS.get(model, MAX_TOKENS)
            res = client.chat(conn, messages, provider=provider, model=model, max_tokens=first,
                              reasoning_effort=effort, _transport=_transport)
            if res.truncated and not parse_verdict(res.text) and first < RETRY_MAX_TOKENS:
                res = client.chat(conn, messages, provider=provider, model=model,
                                  max_tokens=RETRY_MAX_TOKENS, reasoning_effort=effort, _transport=_transport)
        except (client.ProviderError, quota.QuotaExceeded) as e:
            results.append(JudgeResult(name, {}, [], f"judge error: {e}", "judge_error", False, ""))
            continue
        data = parse_verdict(res.text) or {}
        if not data:
            retry = messages + [{"role": "assistant", "content": res.text[:2000]},
                                {"role": "user", "content": "That was not valid JSON. Reply with ONLY the JSON object, no prose, no code fences."}]
            try:
                res = client.chat(conn, retry, provider=provider, model=model, max_tokens=first,
                                  reasoning_effort=effort, _transport=_transport)
                data = parse_verdict(res.text) or {}
            except (client.ProviderError, quota.QuotaExceeded):
                data = {}
        scores = {k: _clamp(data.get(k)) for k in RUBRIC} if data else {}
        results.append(JudgeResult(
            judge=name, scores=scores,
            acceptance=normalize_acceptance(data.get("acceptance") or [], criteria) if criteria is not None
            else (data.get("acceptance") or []),
            critique=str(data.get("critique") or ("unparseable judge output" if not data else "")),
            failure_class=str(data.get("failure_class") or ("judge_unparseable" if not data else "none")),
            cached=res.cached, raw_text=res.text,
        ))
    return results


CEILING = 0.95


def trimmed_low_mean(values: list[float]) -> float:
    """Drop the single most lenient score when 3+ judges answered, then average."""
    if not values:
        return 0.0
    kept = sorted(values)[:-1] if len(values) >= 3 else values
    return round(statistics.mean(kept), 3)


def ceiling_aware(values: list[float]) -> float:
    """Two failure modes need opposite cures. Lenient judges park at the ceiling, so when two or more
    scores are >= CEILING we drop the most lenient one (the fabricated-evidence case: 1.0, 1.0, 0.4 -> 0.7).
    Otherwise the judges genuinely disagree and the median is the robust choice, so one factually wrong
    low judge cannot sink correct work (task 5 of 2026-11-03: 1.0, 0.68, 0.5 -> 0.68, not 0.59)."""
    if not values:
        return 0.0
    if len(values) < 3:
        return round(statistics.mean(values), 3)
    if sum(1 for v in values if v >= CEILING) >= 2:
        return trimmed_low_mean(values)
    return round(statistics.median(values), 3)


def aggregate_detail(results: list[JudgeResult]) -> dict:
    """Ceiling-aware aggregate per metric (see `ceiling_aware`); failure class and critique from the
    strictest judge that found a problem (ties broken by majority), because the diagnosis exists to
    surface problems.

    `contested_by` names that judge when it stands alone: no other judge raised any failure and at least two
    others put correctness at the ceiling. The class is still kept, because that is also the shape of the
    2026-11-03 fabricated-evidence case (two lenient judges at 1.0, one strict judge right). It is labelled so
    the fitness table and the evolution diagnosis can show it as a minority view instead of a settled fact."""
    valid = [r for r in results if r.scores]
    if not valid:
        return {"scores": {}, "failure_class": "none", "critique": "none", "contested_by": None}
    scores = {k: ceiling_aware([r.scores[k] for r in valid]) for k in RUBRIC}
    flagged = [r for r in valid if r.failure_class not in ("none", "")]
    if flagged:
        classes = Counter(r.failure_class for r in flagged)
        top_count = classes.most_common(1)[0][1]
        contenders = [r for r in flagged if classes[r.failure_class] == top_count]
        strictest = min(contenders, key=lambda r: (r.scores.get("correctness", 1.0), r.scores.get("evidence", 1.0)))
        others = [r for r in valid if r is not strictest]
        alone = len(flagged) == 1 and sum(1 for r in others if r.scores.get("correctness", 0.0) >= CEILING) >= 2
        return {"scores": scores, "failure_class": strictest.failure_class, "critique": strictest.critique or "none",
                "contested_by": strictest.judge if alone else None}
    return {"scores": scores, "failure_class": "none", "contested_by": None,
            "critique": next((r.critique for r in valid if r.critique and r.critique != "none"), "none")}


def aggregate(results: list[JudgeResult]) -> tuple[dict[str, float], str, str]:
    d = aggregate_detail(results)
    return d["scores"], d["failure_class"], d["critique"]


def ensemble_judges(conn: sqlite3.Connection, task_id: int) -> int:
    row = conn.execute("SELECT evidence_json FROM scores WHERE task_id = ? AND judge_model = 'ensemble'"
                       " AND metric = 'rubric:correctness'", (task_id,)).fetchone()
    if not row or not row["evidence_json"]:
        return 0
    return len(json.loads(row["evidence_json"]).get("judges") or [])


def store_judge_results(conn: sqlite3.Connection, task_id: int, results: list[JudgeResult]) -> dict[str, float]:
    for r in results:
        if r.scores:  # a judge that answers now clears any stale error row from an earlier, failed run
            conn.execute("DELETE FROM scores WHERE task_id = ? AND judge_model = ? AND metric = 'rubric:error'",
                         (task_id, r.judge))
    answered = sum(1 for r in results if r.scores)
    if answered and answered < ensemble_judges(conn, task_id):
        # A rate-limited day must not overwrite a 3-judge verdict with a 1-judge one. Keep the per-judge rows
        # that did answer (they are cached anyway) and leave the stronger ensemble in place.
        # Error rows are stored too, so the cause of every missing verdict stays auditable (round 6 lost 10).
        for r in results:
            if r.scores:
                rows = [(f"rubric:{k}", v, {"critique": r.critique, "failure_class": r.failure_class,
                                             "acceptance": r.acceptance, "cached": r.cached}) for k, v in r.scores.items()]
                checks.store_scores(conn, task_id, rows, judge_model=r.judge)
            else:
                checks.store_scores(conn, task_id, [("rubric:error", 0.0, {"critique": r.critique})], judge_model=r.judge)
        return {}
    for r in results:
        if not r.scores:
            checks.store_scores(conn, task_id, [("rubric:error", 0.0, {"critique": r.critique})], judge_model=r.judge)
            continue
        rows = [(f"rubric:{k}", v, {"critique": r.critique, "failure_class": r.failure_class,
                                     "acceptance": r.acceptance, "cached": r.cached}) for k, v in r.scores.items()]
        checks.store_scores(conn, task_id, rows, judge_model=r.judge)
    return _store_ensemble(conn, task_id, results)


def _store_ensemble(conn: sqlite3.Connection, task_id: int, results: list[JudgeResult]) -> dict[str, float]:
    d = aggregate_detail(results)
    if d["scores"]:
        ev = {"failure_class": d["failure_class"], "critique": d["critique"],
              "judges": [r.judge for r in results if r.scores]}
        if d["contested_by"]:
            ev["contested_by"] = d["contested_by"]
        rows = [(f"rubric:{k}", v, ev) for k, v in d["scores"].items()]
        checks.store_scores(conn, task_id, rows, judge_model="ensemble")
    return d["scores"]


def reaggregate(conn: sqlite3.Connection, task_id: int) -> bool:
    """Rebuild a task's ensemble from the per-judge rows already stored, with no API calls. Used after an
    aggregation rule changes, so old verdicts follow the new rule without spending free-tier budget.
    Only the judges the current ensemble was built from are used; returns False if any of them is missing."""
    row = conn.execute("SELECT evidence_json FROM scores WHERE task_id = ? AND judge_model = 'ensemble'"
                       " AND metric = 'rubric:correctness'", (task_id,)).fetchone()
    if not row:
        return False
    names = json.loads(row["evidence_json"] or "{}").get("judges") or []
    results = []
    for name in names:
        rows = conn.execute("SELECT metric, value, evidence_json FROM scores WHERE task_id = ? AND judge_model = ?"
                            " AND metric LIKE 'rubric:%' AND metric != 'rubric:error'", (task_id, name)).fetchall()
        have = {r["metric"].removeprefix("rubric:"): r for r in rows}
        if not all(k in have for k in RUBRIC):
            return False
        ev = json.loads(have["correctness"]["evidence_json"] or "{}")
        results.append(JudgeResult(name, {k: have[k]["value"] for k in RUBRIC}, ev.get("acceptance") or [],
                                   ev.get("critique") or "none", ev.get("failure_class") or "none", True, ""))
    _store_ensemble(conn, task_id, results)
    return True
