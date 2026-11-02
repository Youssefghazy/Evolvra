"""Fitness: one number per task, rolled up per agent version. The evolution loop optimizes this."""
from __future__ import annotations

import sqlite3

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


def task_fitness(conn: sqlite3.Connection, task_id: int) -> float | None:
    rows = conn.execute(
        "SELECT metric, value FROM scores WHERE task_id = ? AND judge_model IN ('deterministic','ensemble')",
        (task_id,)).fetchall()
    if not rows:
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
