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
    return [BankTask(t["brief"], t["task"], tuple(t.get("acceptance", [])), "seed") for t in data.get("tasks", [])
            if not requires_execution(t["task"], t.get("acceptance", []))]


_FILE_REF = re.compile(r"\b[\w.-]+\.(md|txt|json|py|js|ts|tsx|html|css|csv|yaml|yml|sql|sh|ps1)\b", re.IGNORECASE)


MATERIALS_CHARS = 6000
# Criteria that can only be met by running something. The arena actor has no tools, so such tasks reward
# "honest hypothetical evidence" at best and fabrication at worst; they are left out of the bank.
_EXECUTION_RE = re.compile(
    r"\b(run|runs|ran|execute[sd]?|exit\s*(code|0|1)|passes?\s+(the\s+)?tests?|pytest|actionlint|npm\s+test|"
    r"lint(er)?\s+(output|passes)|command\s+output|byte-identical|sha-?256|valid\s+yaml)\b", re.IGNORECASE)


def requires_execution(task: str, acceptance: list[str]) -> bool:
    return bool(_EXECUTION_RE.search(" ".join([task, *acceptance])))


def is_self_contained(task: str, acceptance: list[str], depends_on: list[int]) -> bool:
    """A bank task must be playable from its text alone. Tasks that consumed another task's output
    (dependencies, or references to produced files) cannot be judged fairly in the proxy arena
    unless that output is embedded in the task (see `materials_for`)."""
    if depends_on:
        return False
    text = " ".join([task, *acceptance])
    return not _FILE_REF.search(text)


def materials_for(conn: sqlite3.Connection, mission_id: int, depends_on: list[int]) -> str:
    """The text the builder produced for the tasks a QA task depended on, truncated.

    Embedding it turns a file-bound QA task into a self-contained one: the arena actor sees exactly
    what the real QA agent saw, and must verify *this* artefact rather than invent one."""
    from ..evals import checks  # local import: evals already imports from evolve-free modules only

    parts = []
    for no in depends_on:
        row = conn.execute("SELECT agent_slug, task, output_dir FROM tasks WHERE mission_id = ? AND task_no = ?",
                           (mission_id, no)).fetchone()
        if not row:
            continue
        body = checks.read_output(row["output_dir"], per_file=MATERIALS_CHARS // 2, total=MATERIALS_CHARS)
        if body.strip():
            parts.append(f"### Output of task {no} ({row['agent_slug']}: {row['task']})\n{body}")
    return "\n\n".join(parts)


def mission_tasks(conn: sqlite3.Connection, slug: str) -> list[BankTask]:
    rows = conn.execute(
        "SELECT m.id AS mission_id, m.brief, m.external_id, t.task, t.acceptance_json, t.depends_json FROM tasks t"
        " JOIN missions m ON m.id = t.mission_id WHERE t.agent_slug = ? AND t.verdict IS NOT NULL"
        " ORDER BY m.started_at DESC", (slug,)).fetchall()
    out = []
    for r in rows:
        acceptance = json.loads(r["acceptance_json"] or "[]")
        depends = json.loads(r["depends_json"] or "[]")
        if requires_execution(r["task"], acceptance):
            continue
        if is_self_contained(r["task"], acceptance, depends):
            out.append(BankTask(r["brief"], r["task"], tuple(acceptance), r["external_id"]))
            continue
        materials = materials_for(conn, r["mission_id"], depends) if depends else ""
        if not materials:
            continue  # file-bound with nothing to embed: unplayable, skip
        brief = f"{r['brief']}\n\n## Input materials (produced earlier in this mission)\n{materials}"
        out.append(BankTask(brief, r["task"], tuple(acceptance), f"{r['external_id']} (materials embedded)"))
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
