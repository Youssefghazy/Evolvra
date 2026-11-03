import json
import shutil
import subprocess
from pathlib import Path

from evolvra import cli

REPO = Path(__file__).resolve().parents[2]


def test_cycle_no_push_runs_all_stages(tmp_path, evolvra_home, recorder, monkeypatch, capsys):
    fake_repo = tmp_path / "repo"
    shutil.copytree(REPO / "plugin", fake_repo / "plugin")
    (fake_repo / "dashboard" / "public").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(fake_repo)], check=True)

    recorder("start", "--brief", "Cycle me", "--mode", "micro")
    mid = max((evolvra_home / "missions").iterdir()).name
    recorder("task", "add", mid, "--agent", "ux-researcher", "--task", "Guide", "--acceptance", "5 questions")
    recorder("task", "start", mid, "1")
    recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "5 open questions")
    recorder("finish", mid, "--status", "done")

    dbfile = tmp_path / "c.db"
    assert cli.main(["--db", str(dbfile), "import", str(fake_repo / "plugin" / "agents")]) == 0
    assert cli.main(["--db", str(dbfile), "cycle", "--no-judges", "--no-push",
                     "--plugin-dir", str(fake_repo / "plugin" / "agents")]) == 0
    out = capsys.readouterr().out
    assert "ingest: missions added=1" in out and "score: tasks scored=1" in out and "export:" in out
    data = json.loads((fake_repo / "dashboard" / "public" / "data" / "missions.json").read_text(encoding="utf-8"))
    assert data[0]["tasks"][0]["fitness"] is not None


def test_cycle_respects_evolve_interval(tmp_path, evolvra_home, monkeypatch, capsys):
    from evolvra.store import db as dbmod
    dbfile = tmp_path / "i.db"
    conn = dbmod.connect(dbfile)
    conn.execute("INSERT INTO agents (slug, name, division) VALUES ('x','X','testing')")
    conn.execute("INSERT INTO evolutions (agent_id, parent_version, candidate_versions_json) VALUES (1, 1, '[]')")
    conn.commit(); conn.close()
    fake_repo = tmp_path / "repo"
    shutil.copytree(REPO / "plugin", fake_repo / "plugin")
    (fake_repo / "dashboard" / "public").mkdir(parents=True)
    assert cli.main(["--db", str(dbfile), "cycle", "--evolve", "--no-judges", "--no-push",
                     "--plugin-dir", str(fake_repo / "plugin" / "agents")]) == 0
    assert "evolve: skipped, last generation ran 0.0h ago" in capsys.readouterr().out
