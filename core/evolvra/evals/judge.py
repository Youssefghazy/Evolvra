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

# Three free models, two companies, one open-weights: no single vendor's taste dominates.
DEFAULT_JUDGES: tuple[tuple[str, str], ...] = (
    ("groq", "openai/gpt-oss-120b"),
    ("gemini", "gemini-3.5-flash-lite"),
    ("gemini", "gemma-4-31b-it"),
)
RUBRIC = ("correctness", "completeness", "quality", "evidence")

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

# Acceptance criteria
{criteria}

# Attempts: {attempts}   Final verdict recorded by the orchestrator: {verdict}
# Agent's own evidence statement
{evidence}

# Output files
{output}

# Grade
Return JSON with exactly these keys:
{{
  "acceptance": [{{"criterion": "<text>", "met": true|false, "reason": "<short>"}}],
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


def render_prompt(*, brief: str, agent: str, agent_description: str, task: str, criteria: list[str],
                  attempts: int, verdict: str | None, evidence: str | None, output: str | None) -> str:
    return PROMPT.format(
        brief=brief,
        agent=agent,
        agent_description=agent_description or "(unknown)",
        task=task,
        criteria="\n".join(f"- {c}" for c in criteria) or "- (none given)",
        attempts=attempts,
        verdict=verdict or "none",
        evidence=(evidence or "(no evidence statement)").strip(),
        output=output or "(no output files found)",
    )


def build_prompt(task: sqlite3.Row, brief: str, agent_description: str) -> str:
    attempts = json.loads(task["attempts_json"] or "[]")
    last = attempts[-1] if attempts else {}
    return render_prompt(
        brief=brief, agent=task["agent_slug"], agent_description=agent_description, task=task["task"],
        criteria=json.loads(task["acceptance_json"] or "[]"), attempts=task["attempts"],
        verdict=task["verdict"], evidence=last.get("evidence"), output=checks.read_output(task["output_dir"]),
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


def _clamp(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def judge_task(conn: sqlite3.Connection, task: sqlite3.Row, brief: str, agent_description: str,
               judges: list[tuple[str, str]] | None = None, *, _transport=None) -> list[JudgeResult]:
    return judge_prompt(conn, build_prompt(task, brief, agent_description), judges, _transport=_transport)


def judge_prompt(conn: sqlite3.Connection, prompt: str, judges: list[tuple[str, str]] | None = None, *,
                 _transport=None) -> list[JudgeResult]:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    results: list[JudgeResult] = []
    for provider, model in judges or judges_from_env():
        name = f"{provider}/{model}"
        try:
            res = client.chat(conn, messages, provider=provider, model=model, max_tokens=900,
                              _transport=_transport)
        except (client.ProviderError, quota.QuotaExceeded) as e:
            results.append(JudgeResult(name, {}, [], f"judge error: {e}", "judge_error", False, ""))
            continue
        data = parse_judge_json(res.text) or {}
        scores = {k: _clamp(data.get(k)) for k in RUBRIC} if data else {}
        results.append(JudgeResult(
            judge=name, scores=scores, acceptance=data.get("acceptance") or [],
            critique=str(data.get("critique") or ("unparseable judge output" if not data else "")),
            failure_class=str(data.get("failure_class") or ("judge_unparseable" if not data else "none")),
            cached=res.cached, raw_text=res.text,
        ))
    return results


def aggregate(results: list[JudgeResult]) -> tuple[dict[str, float], str, str]:
    """Median per metric across judges that answered; majority failure class; first critique."""
    valid = [r for r in results if r.scores]
    scores = {k: round(statistics.median(r.scores[k] for r in valid), 3) for k in RUBRIC} if valid else {}
    classes = Counter(r.failure_class for r in valid if r.failure_class not in ("none", ""))
    failure = classes.most_common(1)[0][0] if classes else "none"
    critique = next((r.critique for r in valid if r.critique and r.critique != "none"), "none")
    return scores, failure, critique


def store_judge_results(conn: sqlite3.Connection, task_id: int, results: list[JudgeResult]) -> dict[str, float]:
    for r in results:
        if not r.scores:
            checks.store_scores(conn, task_id, [("rubric:error", 0.0, {"critique": r.critique})], judge_model=r.judge)
            continue
        rows = [(f"rubric:{k}", v, {"critique": r.critique, "failure_class": r.failure_class,
                                     "acceptance": r.acceptance, "cached": r.cached}) for k, v in r.scores.items()]
        checks.store_scores(conn, task_id, rows, judge_model=r.judge)
    scores, failure, critique = aggregate(results)
    if scores:
        rows = [(f"rubric:{k}", v, {"failure_class": failure, "critique": critique,
                                     "judges": [r.judge for r in results if r.scores]}) for k, v in scores.items()]
        checks.store_scores(conn, task_id, rows, judge_model="ensemble")
    return scores
