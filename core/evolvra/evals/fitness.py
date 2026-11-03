"""Fitness: one number per task, rolled up per agent version. The evolution loop optimizes this."""
from __future__ import annotations

import json
import sqlite3

MIN_JUDGES = 2  # an ensemble backed by fewer judges is provisional and does not count toward fitness

# Weights sum to 1. Correctness dominates; evidence and efficiency keep agents honest and fast.
WEIGHTS = {
    "rubric:correctness": 0.35,
    "rubric:completeness": 0.15,
    "rubric:quality": 0.15,
    "rubric:evidence": 0.10,
    "det:verdict": 0.10,
    "det:efficiency": 0.10,
    "det:output_exists": 0.05,
}


def task_fitness(conn: sqlite3.Connection, task_id: int, *, min_judges: int = MIN_JUDGES) -> float | None:
    """Weighted fitness, or None while the verdict is provisional (fewer than `min_judges` judges answered).
    A single lenient judge inflated four agents on 2026-11-03; provisional tasks wait for the re-score."""
    rows = conn.execute(
        "SELECT metric, value, evidence_json FROM scores WHERE task_id = ?"
        " AND judge_model IN ('deterministic','ensemble')", (task_id,)).fetchall()
    if not rows:
        return None
    ens = next((r for r in rows if r["metric"] == "rubric:correctness"), None)
    if ens is not None:
        # judges ran: a verdict backed by too few of them is provisional. No ensemble at all (judges never
        # ran, e.g. `score --no-judges`) still yields the coarse deterministic-only fitness.
        judges = len(json.loads(ens["evidence_json"] or "{}").get("judges") or [])
        if judges < min_judges:
            return None
    have = {r["metric"]: r["value"] for r in rows}
    total, weight = 0.0, 0.0
    for metric, w in WEIGHTS.items():
        if metric in have:
            total += w * have[metric]
            weight += w
    return round(total / weight, 4) if weight else None


def agent_fitness(conn: sqlite3.Connection) -> list[dict]:
    """Per agent version: tasks scored, mean fitness, and the most common failure class."""
    tasks = conn.execute(
        "SELECT t.id, t.agent_slug, COALESCE(v.version, 0) AS version"
        " FROM tasks t LEFT JOIN agent_versions v ON v.id = t.agent_version_id"
        " WHERE t.verdict IS NOT NULL").fetchall()
    buckets: dict[tuple[str, int], list[float]] = {}
    for t in tasks:
        f = task_fitness(conn, t["id"])
        if f is not None:
            buckets.setdefault((t["agent_slug"], t["version"]), []).append(f)
    out = []
    for (slug, version), values in sorted(buckets.items()):
        failure = conn.execute(
            "SELECT json_extract(s.evidence_json, '$.failure_class') AS fc, COUNT(*) AS n"
            " FROM scores s JOIN tasks t ON t.id = s.task_id"
            " LEFT JOIN agent_versions v ON v.id = t.agent_version_id"
            " WHERE t.agent_slug = ? AND COALESCE(v.version, 0) = ? AND s.judge_model = 'ensemble'"
            " AND s.metric = 'rubric:correctness' AND fc IS NOT NULL AND fc != 'none'"
            " GROUP BY fc ORDER BY n DESC LIMIT 1", (slug, version)).fetchone()
        out.append({
            "agent": slug, "version": version, "tasks": len(values),
            "fitness": round(sum(values) / len(values), 4),
            "min": round(min(values), 3), "max": round(max(values), 3),
            "top_failure": failure["fc"] if failure else None,
        })
    return sorted(out, key=lambda r: r["fitness"])
