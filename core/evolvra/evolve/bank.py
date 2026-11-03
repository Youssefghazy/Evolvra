"""Held-out task bank per agent: seed tasks shipped with the plugin + tasks from real missions."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BankTask:
    brief: str
    task: str
    acceptance: tuple[str, ...]
    source: str  # 'seed' | mission external id

    @property
    def key(self) -> str:
        return self.task.strip().lower()


def seed_tasks(plugin_agents_dir: Path, slug: str) -> list[BankTask]:
    path = plugin_agents_dir / "bank" / f"{slug}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [BankTask(t["brief"], t["task"], tuple(t.get("acceptance", [])), "seed") for t in data.get("tasks", [])]


def mission_tasks(conn: sqlite3.Connection, slug: str) -> list[BankTask]:
    rows = conn.execute(
        "SELECT m.brief, m.external_id, t.task, t.acceptance_json FROM tasks t"
        " JOIN missions m ON m.id = t.mission_id WHERE t.agent_slug = ? AND t.verdict IS NOT NULL"
        " ORDER BY m.started_at DESC", (slug,)).fetchall()
    return [BankTask(r["brief"], r["task"], tuple(json.loads(r["acceptance_json"] or "[]")), r["external_id"])
            for r in rows]


def load_bank(conn: sqlite3.Connection, plugin_agents_dir: Path, slug: str, *, size: int | None = None) -> list[BankTask]:
    """Real mission tasks first (they reflect actual use), then seeds; deduplicated by task text."""
    seen, out = set(), []
    for t in mission_tasks(conn, slug) + seed_tasks(plugin_agents_dir, slug):
        if t.key in seen:
            continue
        seen.add(t.key)
        out.append(t)
    return out[:size] if size else out
