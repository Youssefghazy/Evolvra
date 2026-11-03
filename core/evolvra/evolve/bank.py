"""Held-out task bank per agent: seed tasks shipped with the plugin + tasks from real missions."""
from __future__ import annotations

import json
import re
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


_FILE_REF = re.compile(r"\b[\w.-]+\.(md|txt|json|py|js|ts|tsx|html|css|csv|yaml|yml|sql|sh|ps1)\b", re.IGNORECASE)


def is_self_contained(task: str, acceptance: list[str], depends_on: list[int]) -> bool:
    """A bank task must be playable from its text alone. Tasks that consumed another task's output
    (dependencies, or references to produced files) cannot be judged fairly in the proxy arena:
    the actor has no files, so honest personas lose to ones that invent measurements."""
    if depends_on:
        return False
    text = " ".join([task, *acceptance])
    return not _FILE_REF.search(text)


def mission_tasks(conn: sqlite3.Connection, slug: str) -> list[BankTask]:
    rows = conn.execute(
        "SELECT m.brief, m.external_id, t.task, t.acceptance_json, t.depends_json FROM tasks t"
        " JOIN missions m ON m.id = t.mission_id WHERE t.agent_slug = ? AND t.verdict IS NOT NULL"
        " ORDER BY m.started_at DESC", (slug,)).fetchall()
    out = []
    for r in rows:
        acceptance = json.loads(r["acceptance_json"] or "[]")
        if not is_self_contained(r["task"], acceptance, json.loads(r["depends_json"] or "[]")):
            continue
        out.append(BankTask(r["brief"], r["task"], tuple(acceptance), r["external_id"]))
    return out


def load_bank(conn: sqlite3.Connection, plugin_agents_dir: Path, slug: str, *, size: int | None = None) -> list[BankTask]:
    """Real mission tasks first (they reflect actual use), then seeds; deduplicated by task text."""
    seen, out = set(), []
    for t in mission_tasks(conn, slug) + seed_tasks(plugin_agents_dir, slug):
        if t.key in seen:
            continue
        seen.add(t.key)
        out.append(t)
    return out[:size] if size else out
