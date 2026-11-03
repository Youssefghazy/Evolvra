"""Build the diagnosis packet: what an agent got wrong, with the evidence attached."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from ..evals import checks, fitness


@dataclass
class Diagnosis:
    slug: str
    version: int
    tasks_scored: int
    mean_fitness: float | None
    failure_classes: list[tuple[str, int]]
    worst: list[dict] = field(default_factory=list)   # worst tasks with critiques, misses, output excerpt

    def to_markdown(self) -> str:
        lines = [f"# Diagnosis: {self.slug} v{self.version}", "",
                 f"Tasks scored: {self.tasks_scored}. Mean fitness: {self.mean_fitness if self.mean_fitness is not None else 'n/a'}.", ""]
        if self.failure_classes:
            lines.append("## Failure classes (ensemble majority, most frequent first)")
            lines += [f"- `{fc}` x{n}" for fc, n in self.failure_classes]
            lines.append("")
        if self.worst:
            lines.append("## Worst tasks")
            for w in self.worst:
                lines += [f"### {w['mission']} #{w['task_no']} (fitness {w['fitness']})",
                          f"- Task: {w['task']}",
                          f"- Acceptance: {'; '.join(w['acceptance']) or '(none)'}",
                          f"- Verdict: {w['verdict']} after {w['attempts']} attempt(s)",
                          f"- Failure class: `{w['failure_class']}`",
                          f"- Critique: {w['critique']}"]
                if w["misses"]:
                    lines.append("- Unmet criteria:")
                    lines += [f"  - {m['criterion']}: {m['reason']}" for m in w["misses"]]
                if w["feedback"]:
                    lines.append(f"- QA feedback on failed attempts: {w['feedback']}")
                if w["output_excerpt"]:
                    lines += ["- Output excerpt:", "```", w["output_excerpt"][:1500], "```"]
                lines.append("")
        else:
            lines.append("No scored tasks yet; evolution will rely on the held-out bank alone.")
        return "\n".join(lines)


def diagnose(conn: sqlite3.Connection, slug: str, *, worst_n: int = 3) -> Diagnosis:
    agent = conn.execute("SELECT id, current_version FROM agents WHERE slug = ?", (slug,)).fetchone()
    if not agent:
        raise ValueError(f"unknown agent '{slug}'")
    rows = conn.execute(
        "SELECT t.id, t.task_no, t.task, t.acceptance_json, t.verdict, t.attempts, t.attempts_json, t.output_dir,"
        " m.external_id FROM tasks t JOIN missions m ON m.id = t.mission_id"
        " WHERE t.agent_slug = ? AND t.verdict IS NOT NULL", (slug,)).fetchall()
    scored = []
    for r in rows:
        f = fitness.task_fitness(conn, r["id"])
        if f is None:
            continue
        ens = conn.execute(
            "SELECT evidence_json FROM scores WHERE task_id = ? AND judge_model = 'ensemble'"
            " AND metric = 'rubric:correctness'", (r["id"],)).fetchone()
        ev = json.loads(ens["evidence_json"]) if ens else {}
        misses = []
        for j in conn.execute("SELECT evidence_json FROM scores WHERE task_id = ? AND judge_model NOT IN"
                              " ('ensemble','deterministic') AND metric = 'rubric:correctness'", (r["id"],)):
            for a in (json.loads(j["evidence_json"]).get("acceptance") or []):
                if a.get("met") is False and a.get("criterion"):
                    misses.append({"criterion": a["criterion"], "reason": a.get("reason", "")})
        attempts = json.loads(r["attempts_json"] or "[]")
        feedback = " | ".join(a["feedback"] for a in attempts if a.get("feedback"))
        scored.append({
            "task_id": r["id"], "mission": r["external_id"], "task_no": r["task_no"], "task": r["task"],
            "acceptance": json.loads(r["acceptance_json"] or "[]"), "verdict": r["verdict"],
            "attempts": r["attempts"], "fitness": f, "failure_class": ev.get("failure_class", "none"),
            "critique": ev.get("critique", ""), "misses": _dedupe(misses), "feedback": feedback,
            "output_excerpt": checks.read_output(r["output_dir"], per_file=1200, total=1500),
        })
    scored.sort(key=lambda s: s["fitness"])
    counts: dict[str, int] = {}
    for s in scored:
        if s["failure_class"] not in ("none", "", None):
            counts[s["failure_class"]] = counts.get(s["failure_class"], 0) + 1
    mean = round(sum(s["fitness"] for s in scored) / len(scored), 4) if scored else None
    return Diagnosis(slug, agent["current_version"], len(scored), mean,
                     sorted(counts.items(), key=lambda kv: -kv[1]), scored[:worst_n])


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        k = it["criterion"].strip().lower()
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out
