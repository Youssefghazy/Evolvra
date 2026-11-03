"""Export JSON snapshots for the static dashboard. Pure reads; safe to run any time."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from . import __version__
from .evals import fitness
from .missions import ingest


def export_all(conn: sqlite3.Connection, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    agents = _agents(conn)
    missions = _missions(conn)
    evolutions = _evolutions(conn)
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evolvra_version": __version__,
        "agents": len(agents),
        "versions": sum(len(a["versions"]) for a in agents),
        "missions": len(missions),
        "tasks": sum(len(m["tasks"]) for m in missions),
        "evolutions": len(evolutions),
        "promotions": sum(1 for e in evolutions if e["winner_version"]),
        "providers": [dict(r) for r in conn.execute(
            "SELECT provider, SUM(requests) AS requests, SUM(tokens) AS tokens FROM provider_usage GROUP BY provider")],
    }
    files = {"agents.json": agents, "missions.json": missions, "evolutions.json": evolutions, "summary.json": summary}
    for name, data in files.items():
        (out_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {k: (len(v) if isinstance(v, list) else 1) for k, v in files.items()}


def _agents(conn: sqlite3.Connection) -> list[dict]:
    fit = {(r["agent"], r["version"]): r for r in fitness.agent_fitness(conn)}
    out = []
    for a in conn.execute("SELECT * FROM agents ORDER BY division, slug"):
        versions = []
        for v in conn.execute("SELECT * FROM agent_versions WHERE agent_id = ? ORDER BY version", (a["id"],)):
            f = fit.get((a["slug"], v["version"]))
            versions.append({
                "version": v["version"], "parent": v["parent_version"], "created_by": v["created_by"],
                "rationale": v["rationale"], "created_at": v["created_at"], "sha": v["content_sha"][:12],
                "content": v["content_md"],
                "fitness": f["fitness"] if f else None, "tasks": f["tasks"] if f else 0,
                "top_failure": f["top_failure"] if f else None,
            })
        current = next((v for v in versions if v["version"] == a["current_version"]), None)
        out.append({
            "slug": a["slug"], "name": a["name"], "division": a["division"], "emoji": a["emoji"], "color": a["color"],
            "current_version": a["current_version"], "fitness": current["fitness"] if current else None,
            "tasks": sum(v["tasks"] for v in versions), "versions": versions,
        })
    return out


def _missions(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for m in ingest.list_missions(conn, last=500):
        detail, tasks = ingest.mission_detail(conn, m["external_id"])
        out.append({
            "id": m["external_id"], "brief": m["brief"], "mode": m["mode"], "status": m["status"],
            "summary": detail["summary"], "started_at": m["started_at"], "finished_at": m["finished_at"],
            "tasks": [{
                "no": t["task_no"], "agent": t["agent_slug"], "task": t["task"],
                "acceptance": json.loads(t["acceptance_json"] or "[]"), "status": t["status"],
                "attempts": t["attempts"], "verdict": t["verdict"], "attempt_log": json.loads(t["attempts_json"] or "[]"),
                "traces": t["trace_count"], "fitness": fitness.task_fitness(conn, t["id"]),
                "provisional": fitness.task_fitness(conn, t["id"]) is None
                and fitness.task_fitness(conn, t["id"], min_judges=1) is not None,
                "scores": _task_scores(conn, t["id"]),
            } for t in tasks],
        })
    return out


def _task_scores(conn: sqlite3.Connection, task_id: int) -> list[dict]:
    return [{"metric": r["metric"], "value": r["value"], "judge": r["judge_model"],
             "evidence": json.loads(r["evidence_json"]) if r["evidence_json"] else None}
            for r in conn.execute("SELECT metric, value, judge_model, evidence_json FROM scores WHERE task_id = ?"
                                  " ORDER BY judge_model, metric", (task_id,))]


def _evolutions(conn: sqlite3.Connection) -> list[dict]:
    return [{
        "id": e["id"], "agent": e["slug"], "parent_version": e["parent_version"],
        "winner_version": e["winner_version"], "delta": e["bank_delta"], "created_at": e["created_at"],
        "parent_fitness": e["parent_fitness"], "bank": json.loads(e["bank_json"] or "[]"),
        "candidates": json.loads(e["candidate_versions_json"] or "[]"), "diagnosis": e["diagnosis_md"],
    } for e in conn.execute("SELECT e.*, a.slug FROM evolutions e JOIN agents a ON a.id = e.agent_id"
                            " ORDER BY e.created_at")]
