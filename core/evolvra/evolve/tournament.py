"""Proxy tournament: an 'actor' model plays each persona on held-out tasks; the judge ensemble grades.

This is how GEPA-style optimizers evaluate prompt candidates without a human in the loop. The actor
is a free model, not Claude, so absolute scores are a proxy; the *relative* ranking between parent and
variants is the signal. The real deployment still runs inside Claude Code.
"""
from __future__ import annotations

import os
import sqlite3
import statistics
from dataclasses import dataclass, field

from ..evals import judge
from ..router import client, quota
from .bank import BankTask

# Flash-Lite answers fast and its free tier has a large per-minute token budget. Groq gpt-oss-120b is
# stronger but capped at 8k tokens/minute on the free tier, which persona-sized prompts exhaust.
DEFAULT_ACTOR = ("gemini", "gemini-3.5-flash-lite")
PROXY_WEIGHTS = {"correctness": 0.4, "completeness": 0.2, "quality": 0.2, "evidence": 0.2}

ACTOR_PROMPT = """# Mission brief
{brief}

# Your task
{task}

# Acceptance criteria
{criteria}

Produce the deliverable now, in Markdown. Be concrete and complete.

Important: in this exercise you have NO file access and NO tool execution. Do not invent measurements,
command output, or file contents. Where verification would require running something, state exactly
what you would run and what result would count as PASS. Invented numbers are a failure.

End with a section titled "## Evidence" that states, for each acceptance criterion, how your deliverable
satisfies it, or what is needed to verify it."""

PROXY_JUDGE_NOTE = """

# Arena note
This deliverable was produced in a sandbox with NO file access and NO tool execution. Any specific
measurement, command output, or file content it claims to have observed is fabricated and must be scored
low on evidence and correctness. A deliverable that honestly states what it would run and what would count
as PASS is the correct behaviour here and must not be penalised for the missing numbers."""


@dataclass
class TaskResult:
    task: BankTask
    output: str
    scores: dict[str, float]
    proxy_fitness: float | None
    failure_class: str
    critique: str
    judge_errors: int


@dataclass
class PersonaResult:
    label: str
    results: list[TaskResult] = field(default_factory=list)

    @property
    def fitness(self) -> float | None:
        vals = [r.proxy_fitness for r in self.results if r.proxy_fitness is not None]
        return round(statistics.mean(vals), 4) if vals else None

    @property
    def scored_tasks(self) -> dict[str, float]:
        return {r.task.key: r.proxy_fitness for r in self.results if r.proxy_fitness is not None}


def paired_delta(candidate: PersonaResult, parent: PersonaResult) -> tuple[float | None, int]:
    """Mean (candidate - parent) over tasks BOTH completed, and how many tasks that is.

    Comparing on different task subsets would reward whichever persona happened to hit fewer
    rate limits, so only shared tasks count.
    """
    a, b = candidate.scored_tasks, parent.scored_tasks
    shared = [k for k in a if k in b]
    if not shared:
        return None, 0
    return round(statistics.mean(a[k] - b[k] for k in shared), 4), len(shared)


def actor_from_env() -> tuple[str, str]:
    spec = os.environ.get("EVOLVRA_ACTOR")
    if spec and ":" in spec:
        p, _, m = spec.partition(":")
        return p.strip(), m.strip()
    return DEFAULT_ACTOR


def proxy_fitness(scores: dict[str, float]) -> float | None:
    if not scores:
        return None
    return round(sum(PROXY_WEIGHTS[k] * scores.get(k, 0.0) for k in PROXY_WEIGHTS), 4)


def split_evidence(output: str) -> tuple[str, str]:
    marker = "## Evidence"
    idx = output.find(marker)
    if idx == -1:
        return output, ""
    return output[:idx].rstrip(), output[idx + len(marker):].strip()


def play(conn: sqlite3.Connection, persona_text: str, label: str, bank: list[BankTask], *,
         agent_slug: str, agent_description: str, actor: tuple[str, str] | None = None,
         judges: list[tuple[str, str]] | None = None, _transport=None) -> PersonaResult:
    provider, model = actor or actor_from_env()
    pr = PersonaResult(label)
    for t in bank:
        user = ACTOR_PROMPT.format(brief=t.brief, task=t.task,
                                   criteria="\n".join(f"- {c}" for c in t.acceptance) or "- (none)")
        try:
            res = client.chat(conn, [{"role": "system", "content": persona_text}, {"role": "user", "content": user}],
                              provider=provider, model=model, max_tokens=2500, temperature=0.2,
                              _transport=_transport)
            output = res.text
        except (client.ProviderError, quota.QuotaExceeded) as e:
            pr.results.append(TaskResult(t, "", {}, None, "actor_error", f"actor error: {e}", 0))
            continue
        body, evidence = split_evidence(output)
        prompt = judge.render_prompt(brief=t.brief, agent=agent_slug, agent_description=agent_description,
                                     task=t.task, criteria=list(t.acceptance), attempts=1, verdict="PASS",
                                     evidence=evidence, output=body) + PROXY_JUDGE_NOTE
        jr = judge.judge_prompt(conn, prompt, judges, _transport=_transport)
        scores, failure, critique = judge.aggregate(jr)
        pr.results.append(TaskResult(t, output, scores, proxy_fitness(scores), failure, critique,
                                     sum(1 for r in jr if not r.scores)))
    return pr
