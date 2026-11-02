"""Ingest recorder output into SQLite: missions/*/mission.json and traces.jsonl.

Both ingests are idempotent. Missions are upserted by their external id; traces are
keyed by line number in traces.jsonl and the file offset is remembered, so re-running
`evolvra ingest` only processes what is new.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from ..store import db

VALID_MODES = {"micro", "sprint", "full"}
VALID_MISSION_STATUS = {"running", "done", "failed", "escalated"}
VALID_TASK_STATUS = {"pending", "running", "done", "escalated"}
VALID_VERDICTS = {"PASS", "FAIL", "NEEDS_WORK", None}


@dataclass
class IngestReport:
    missions_added: int = 0
    missions_updated: int = 0
    missions_invalid: list[tuple[str, str]] = field(default_factory=list)
    traces_added: int = 0
    traces_skipped: int = 0

    def summary(self) -> str:
        missions = (f"missions added={self.missions_added} updated={self.missions_updated}"
                    f" invalid={len(self.missions_invalid)}")
        traces = f"traces added={self.traces_added} skipped={self.traces_skipped}"
        return f"{missions} | {traces}"


def validate_mission(m: dict) -> list[str]:
    errors: list[str] = []
    for key in ("id", "brief", "mode", "status", "started_at", "tasks"):
        if key not in m:
            errors.append(f"missing field: {key}")
    if errors:
        return errors
    if m["mode"] not in VALID_MODES:
        errors.append(f"bad mode: {m['mode']}")
    if m["status"] not in VALID_MISSION_STATUS:
        errors.append(f"bad status: {m['status']}")
    if not isinstance(m["tasks"], list):
        return errors + ["tasks must be a list"]
    seen = set()
    for t in m["tasks"]:
        no = t.get("no")
        if not isinstance(no, int) or no in seen:
            errors.append(f"task has bad or duplicate 'no': {no!r}")
        seen.add(no)
        for key in ("agent", "task", "status", "attempts"):
            if key not in t:
                errors.append(f"task {no}: missing field {key}")
        if t.get("status") not in VALID_TASK_STATUS:
            errors.append(f"task {no}: bad status {t.get('status')!r}")
        for a in t.get("attempts", []):
            if a.get("verdict") not in VALID_VERDICTS:
                errors.append(f"task {no}: bad verdict {a.get('verdict')!r}")
    return errors


def ingest_missions(conn: sqlite3.Connection, missions_dir: Path, report: IngestReport | None = None) -> IngestReport:
    report = report or IngestReport()
    if not missions_dir.is_dir():
        return report
    for path in sorted(missions_dir.glob("*/mission.json")):
        try:
            m = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            report.missions_invalid.append((str(path), f"unreadable: {e}"))
            continue
        errors = validate_mission(m)
        if errors:
            report.missions_invalid.append((str(path), "; ".join(errors)))
            continue
        _upsert_mission(conn, m, path, report)
    conn.commit()
    return report


def _upsert_mission(conn: sqlite3.Connection, m: dict, path: Path, report: IngestReport) -> None:
    row = conn.execute("SELECT id FROM missions WHERE external_id = ?", (m["id"],)).fetchone()
    values = (m["brief"], m["mode"], m["status"], m.get("summary"), m["started_at"],
              m.get("finished_at"), str(path))
    if row is None:
        cur = conn.execute(
            "INSERT INTO missions (external_id, brief, mode, status, summary, started_at, finished_at, source_path)"
            " VALUES (?,?,?,?,?,?,?,?)", (m["id"], *values))
        mission_id = cur.lastrowid
        report.missions_added += 1
    else:
        mission_id = row["id"]
        conn.execute(
            "UPDATE missions SET brief=?, mode=?, status=?, summary=?, started_at=?, finished_at=?, source_path=?"
            " WHERE id=?", (*values, mission_id))
        report.missions_updated += 1

    for t in m["tasks"]:
        attempts = t.get("attempts", [])
        last = attempts[-1] if attempts else {}
        version_id = _current_version_id(conn, t["agent"])
        conn.execute(
            "INSERT INTO tasks (mission_id, task_no, agent_slug, agent_version_id, task, acceptance_json,"
            " depends_json, status, attempts, verdict, attempts_json, output_dir, started_at, finished_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(mission_id, task_no) DO UPDATE SET agent_slug=excluded.agent_slug,"
            " agent_version_id=COALESCE(tasks.agent_version_id, excluded.agent_version_id), task=excluded.task,"
            " acceptance_json=excluded.acceptance_json, depends_json=excluded.depends_json,"
            " status=excluded.status, attempts=excluded.attempts, verdict=excluded.verdict,"
            " attempts_json=excluded.attempts_json, output_dir=excluded.output_dir,"
            " started_at=excluded.started_at, finished_at=excluded.finished_at",
            (mission_id, t["no"], t["agent"], version_id, t["task"],
             json.dumps(t.get("acceptance", [])), json.dumps(t.get("depends_on", [])),
             t["status"], len(attempts), last.get("verdict"), json.dumps(attempts),
             t.get("output_dir"), attempts[0].get("started_at") if attempts else None,
             last.get("finished_at")),
        )


def _current_version_id(conn: sqlite3.Connection, slug: str) -> int | None:
    row = conn.execute(
        "SELECT v.id FROM agent_versions v JOIN agents a ON a.id = v.agent_id"
        " WHERE a.slug = ? AND v.version = a.current_version", (slug,)).fetchone()
    return row["id"] if row else None


def ingest_traces(conn: sqlite3.Connection, traces_path: Path, report: IngestReport | None = None) -> IngestReport:
    report = report or IngestReport()
    if not traces_path.is_file():
        return report
    state = conn.execute("SELECT value FROM ingest_state WHERE key = 'traces_line'").fetchone()
    start_line = int(state["value"]) if state else 0
    with traces_path.open(encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            if line_no <= start_line:
                report.traces_skipped += 1
                continue
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                report.traces_skipped += 1
                continue
            mission_id, task_id = _resolve_task(conn, ev.get("mission"), ev.get("task_no"))
            conn.execute(
                "INSERT OR IGNORE INTO traces (line_no, mission_id, task_id, session_id, event, tool,"
                " args_json, result_json, agent, ts) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (line_no, mission_id, task_id, ev.get("session_id"), ev.get("event") or "unknown",
                 ev.get("tool_name"), json.dumps(ev.get("tool_input")), json.dumps(ev.get("tool_response")),
                 ev.get("agent"), ev.get("ts") or ""),
            )
            report.traces_added += 1
            last = line_no
    if report.traces_added:
        conn.execute("INSERT OR REPLACE INTO ingest_state (key, value) VALUES ('traces_line', ?)", (str(last),))
    conn.commit()
    return report


def _resolve_task(conn: sqlite3.Connection, external_id, task_no) -> tuple[int | None, int | None]:
    if not external_id:
        return None, None
    m = conn.execute("SELECT id FROM missions WHERE external_id = ?", (external_id,)).fetchone()
    if not m:
        return None, None
    if task_no is None:
        return m["id"], None
    t = conn.execute("SELECT id FROM tasks WHERE mission_id = ? AND task_no = ?", (m["id"], task_no)).fetchone()
    return m["id"], (t["id"] if t else None)


def ingest_all(conn: sqlite3.Connection, home: Path | None = None) -> IngestReport:
    home = home or db.evolvra_home()
    report = IngestReport()
    ingest_missions(conn, home / "missions", report)   # missions first so traces can link
    ingest_traces(conn, home / "traces.jsonl", report)
    return report


# ---- queries used by the CLI and (later) the dashboard export ----------------

def list_missions(conn: sqlite3.Connection, last: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT m.external_id, m.brief, m.mode, m.status, m.started_at, m.finished_at,"
        " COUNT(t.id) AS tasks, SUM(t.status = 'done') AS tasks_done, SUM(t.attempts) AS attempts"
        " FROM missions m LEFT JOIN tasks t ON t.mission_id = m.id"
        " GROUP BY m.id ORDER BY m.started_at DESC LIMIT ?", (last,)).fetchall()


def mission_detail(conn: sqlite3.Connection, external_id: str) -> tuple[sqlite3.Row | None, list[sqlite3.Row]]:
    m = conn.execute("SELECT * FROM missions WHERE external_id = ?", (external_id,)).fetchone()
    if not m:
        return None, []
    tasks = conn.execute(
        "SELECT t.*, (SELECT COUNT(*) FROM traces x WHERE x.task_id = t.id) AS trace_count"
        " FROM tasks t WHERE t.mission_id = ? ORDER BY t.task_no", (m["id"],)).fetchall()
    return m, tasks


def agent_stats(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT agent_slug, COUNT(*) AS tasks, SUM(verdict = 'PASS') AS passed,"
        " SUM(verdict IN ('FAIL','NEEDS_WORK')) AS failed, SUM(attempts) AS attempts,"
        " ROUND(AVG(attempts), 2) AS avg_attempts"
        " FROM tasks GROUP BY agent_slug ORDER BY failed DESC, tasks DESC").fetchall()
