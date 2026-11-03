import json
from pathlib import Path

from evolvra import export
from evolvra.evals import runner
from evolvra.missions import ingest
from evolvra.registry import personas
from evolvra.store import db

from .conftest import mission_id

AGENTS_DIR = Path(__file__).resolve().parents[2] / "plugin" / "agents"


def test_export_writes_all_snapshots(tmp_path, evolvra_home, recorder):
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    recorder("start", "--brief", "Export me", "--mode", "micro")
    mid = mission_id(evolvra_home)
    recorder("task", "add", mid, "--agent", "growth-hacker", "--task", "Plan", "--acceptance", "three experiments")
    recorder("task", "start", mid, "1")
    recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "three listed")
    recorder("finish", mid, "--status", "done", "--summary", "ok")
    ingest.ingest_all(conn, evolvra_home)
    runner.score_tasks(conn, runner.pending_tasks(conn), skip_judges=True)

    out = tmp_path / "data"
    counts = export.export_all(conn, out)
    assert counts == {"agents.json": 10, "missions.json": 1, "evolutions.json": 0, "summary.json": 1}
    agents = json.loads((out / "agents.json").read_text(encoding="utf-8"))
    gh = next(a for a in agents if a["slug"] == "growth-hacker")
    assert gh["versions"][0]["content"].startswith("---") and gh["versions"][0]["fitness"] is not None
    missions = json.loads((out / "missions.json").read_text(encoding="utf-8"))
    assert missions[0]["tasks"][0]["scores"] and missions[0]["tasks"][0]["fitness"] is not None
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["agents"] == 10 and summary["tasks"] == 1 and summary["promotions"] == 0
