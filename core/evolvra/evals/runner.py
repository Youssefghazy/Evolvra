"""Score tasks end to end: deterministic checks, judge ensemble, fitness."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from . import checks, fitness, judge

MIN_JUDGES = 2  # below this an ensemble is provisional and the task is re-scored on the next cycle


@dataclass
class ScoreReport:
    tasks_scored: int = 0
    tasks_skipped: int = 0
    judge_calls: int = 0
    judge_cached: int = 0
    judge_errors: int = 0
    fitness: list[tuple[str, int, float | None]] = field(default_factory=list)

    def summary(self) -> str:
        return (f"tasks scored={self.tasks_scored} skipped={self.tasks_skipped} | judge calls={self.judge_calls}"
                f" cached={self.judge_cached} errors={self.judge_errors}")


def pending_tasks(conn: sqlite3.Connection, mission_external_id: str | None = None,
                  rescore: bool = False) -> list[sqlite3.Row]:
    sql = ("SELECT t.*, m.brief, m.external_id,"
           " (SELECT description FROM agent_meta WHERE slug = t.agent_slug) AS agent_description"
           " FROM tasks t JOIN missions m ON m.id = t.mission_id WHERE t.verdict IS NOT NULL")
    args: list = []
    if mission_external_id:
        sql += " AND m.external_id = ?"
        args.append(mission_external_id)
    if not rescore:
        # fully scored = an ensemble row backed by at least MIN_JUDGES answering judges; anything thinner
        # (rate-limited day, dead judge) is picked up again next cycle, and cached verdicts cost nothing
        sql += (" AND NOT EXISTS (SELECT 1 FROM scores s WHERE s.task_id = t.id AND s.judge_model = 'ensemble'"
                " AND s.metric = 'rubric:correctness'"
                f" AND json_array_length(json_extract(s.evidence_json, '$.judges')) >= {MIN_JUDGES})")
    sql += " ORDER BY m.started_at, t.task_no"
    _ensure_agent_meta(conn)
    return conn.execute(sql, args).fetchall()


def _ensure_agent_meta(conn: sqlite3.Connection) -> None:
    """Temp view: agent slug -> description from the current persona frontmatter."""
    conn.execute("""
        CREATE TEMP VIEW IF NOT EXISTS agent_meta AS
        SELECT a.slug AS slug,
               TRIM(SUBSTR(v.content_md, INSTR(v.content_md, 'description:') + 12,
                    INSTR(SUBSTR(v.content_md, INSTR(v.content_md, 'description:') + 12), CHAR(10)) - 1)) AS description
        FROM agents a JOIN agent_versions v ON v.agent_id = a.id AND v.version = a.current_version
    """)


def score_tasks(conn: sqlite3.Connection, tasks: list[sqlite3.Row], judges=None, *, skip_judges: bool = False,
                _transport=None) -> ScoreReport:
    report = ScoreReport()
    for t in tasks:
        checks.store_scores(conn, t["id"], checks.run_checks(t))
        if not skip_judges:
            results = judge.judge_task(conn, t, t["brief"], t["agent_description"] or "", judges, _transport=_transport)
            report.judge_calls += len(results)
            report.judge_cached += sum(r.cached for r in results)
            report.judge_errors += sum(not r.scores for r in results)
            judge.store_judge_results(conn, t["id"], results)
        report.tasks_scored += 1
        report.fitness.append((t["agent_slug"], t["task_no"], fitness.task_fitness(conn, t["id"])))
    return report
