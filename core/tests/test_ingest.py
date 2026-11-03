import json
from pathlib import Path

from evolvra.missions import ingest
from evolvra.registry import personas
from evolvra.store import db

from .conftest import mission_id

AGENTS_DIR = Path(__file__).resolve().parents[2] / "plugin" / "agents"


def _record_mission(evolvra_home, recorder, hook):
    recorder("start", "--brief", "Ingest me please", "--mode", "sprint")
    mid = mission_id(evolvra_home)
    recorder("task", "add", mid, "--agent", "content-creator", "--task", "Write", "--acceptance", "short")
    recorder("task", "add", mid, "--agent", "not-a-real-agent", "--task", "Mystery")
    recorder("task", "start", mid, "1")
    hook({"hook_event_name": "PostToolUse", "session_id": "s", "tool_name": "Write", "tool_input": {}})
    hook({"hook_event_name": "PostToolUse", "session_id": "s", "tool_name": "Bash", "tool_input": {}})
    recorder("task", "done", mid, "1", "--verdict", "FAIL", "--feedback", "longer")
    recorder("task", "start", mid, "1")
    recorder("task", "done", mid, "1", "--verdict", "PASS")
    return mid


def test_ingest_missions_and_traces_is_idempotent(evolvra_home, recorder, hook):
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    mid = _record_mission(evolvra_home, recorder, hook)

    report = ingest.ingest_all(conn, evolvra_home)
    assert report.missions_added == 1 and report.traces_added == 2 and not report.missions_invalid

    m, tasks = ingest.mission_detail(conn, mid)
    assert m["status"] == "running" and m["mode"] == "sprint"
    assert tasks[0]["agent_slug"] == "content-creator" and tasks[0]["agent_version_id"] is not None
    assert tasks[0]["attempts"] == 2 and tasks[0]["verdict"] == "PASS" and tasks[0]["trace_count"] == 2
    assert tasks[1]["agent_version_id"] is None  # unknown slug still ingested, just unlinked

    # finishing the mission and re-ingesting updates rather than duplicates
    recorder("finish", mid, "--status", "done", "--summary", "ok")
    report2 = ingest.ingest_all(conn, evolvra_home)
    assert report2.missions_updated == 1 and report2.missions_added == 0
    assert report2.traces_added == 0 and report2.traces_skipped == 2
    assert conn.execute("SELECT COUNT(*) FROM missions").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0] == 2
    assert ingest.list_missions(conn)[0]["status"] == "done"
    stats = {r["agent_slug"]: dict(r) for r in ingest.agent_stats(conn)}
    assert stats["content-creator"]["passed"] == 1 and stats["content-creator"]["attempts"] == 2


def test_invalid_mission_file_is_reported_not_crashed(evolvra_home):
    conn = db.connect(":memory:")
    bad = evolvra_home / "missions" / "bad"
    bad.mkdir(parents=True)
    (bad / "mission.json").write_text(json.dumps({"id": "bad", "brief": "x", "mode": "turbo",
                                                  "status": "running", "started_at": "t", "tasks": []}))
    (evolvra_home / "missions" / "broken").mkdir()
    (evolvra_home / "missions" / "broken" / "mission.json").write_text("{not json")
    report = ingest.ingest_all(conn, evolvra_home)
    assert report.missions_added == 0 and len(report.missions_invalid) == 2
    assert any("bad mode" in why for _, why in report.missions_invalid)


def test_v1_database_upgrades_to_current(tmp_path):
    path = tmp_path / "old.db"
    import sqlite3

    raw = sqlite3.connect(path)
    raw.executescript("CREATE TABLE agents (id INTEGER PRIMARY KEY, slug TEXT); PRAGMA user_version = 1;")
    raw.commit(); raw.close()
    conn = db.connect(path)
    assert db.schema_version(conn) == db.SCHEMA_VERSION
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
    assert {"task_no", "agent_slug", "attempts_json"} <= cols
    indexes = {r[1] for r in conn.execute("PRAGMA index_list(scores)")}
    assert "idx_scores_unique" in indexes


def test_v3_database_gains_evolution_columns(tmp_path):
    import sqlite3

    path = tmp_path / "v3.db"
    raw = sqlite3.connect(path)
    raw.executescript("""
        CREATE TABLE evolutions (id INTEGER PRIMARY KEY, agent_id INTEGER, parent_version INTEGER,
          candidate_versions_json TEXT, winner_version INTEGER, bank_delta REAL, diagnosis_md TEXT, created_at TEXT);
        PRAGMA user_version = 3;""")
    raw.commit(); raw.close()
    conn = db.connect(path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(evolutions)")}
    assert {"parent_fitness", "bank_json"} <= cols and db.schema_version(conn) == db.SCHEMA_VERSION
