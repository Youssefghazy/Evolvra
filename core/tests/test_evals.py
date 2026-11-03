import json
from pathlib import Path

from evolvra.evals import checks, fitness, judge, runner
from evolvra.missions import ingest
from evolvra.registry import personas
from evolvra.store import db

from .conftest import mission_id

AGENTS_DIR = Path(__file__).resolve().parents[2] / "plugin" / "agents"
JUDGES = [("groq", "openai/gpt-oss-120b"), ("gemini", "gemini-3.5-flash-lite"), ("groq", "qwen/qwen3.8-27b")]


def _recorded_mission(evolvra_home, recorder, with_output=True):
    recorder("start", "--brief", "Write a product paragraph for a note app", "--mode", "micro")
    mid = mission_id(evolvra_home)
    recorder("task", "add", mid, "--agent", "content-creator", "--task", "Write it",
             "--acceptance", "under 120 words", "--acceptance", "mentions sync")
    recorder("task", "start", mid, "1")
    if with_output:
        out = evolvra_home / "missions" / mid / "01-content-creator"
        (out / "paragraph.md").write_text("Notely keeps your notes in sync everywhere. " * 5, encoding="utf-8")
    recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "98 words; the word sync appears")
    recorder("finish", mid, "--status", "done")
    return mid


def judge_transport(scores_by_model):
    calls = []

    def _t(url, body, api_key, timeout):
        calls.append(body)
        model = body["model"]
        reply = scores_by_model[model]
        return {"choices": [{"message": {"content": reply}, "finish_reason": "stop"}], "usage": {"total_tokens": 50}}

    _t.calls = calls
    return _t


def _reply(c, q, fc="none", fence=False):
    obj = {"acceptance": [{"criterion": "under 120 words", "met": True, "reason": "98"}],
           "correctness": c, "completeness": 0.9, "quality": q, "evidence": 0.8,
           "critique": "fine" if fc == "none" else "too generic", "failure_class": fc}
    text = json.dumps(obj)
    return f"Here you go:\n```json\n{text}\n```" if fence else text


def test_deterministic_checks(evolvra_home, recorder):
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder)
    ingest.ingest_all(conn, evolvra_home)
    task = runner.pending_tasks(conn)[0]
    results = {m: v for m, v, _ in checks.run_checks(task)}
    assert results == {"det:output_exists": 1.0, "det:evidence_present": 1.0, "det:efficiency": 1.0, "det:verdict": 1.0}
    assert "paragraph.md" in checks.read_output(task["output_dir"])
    assert task["agent_description"].startswith("Expert")  # pulled from persona frontmatter


def test_output_files_skip_virtualenvs_and_hidden_dirs(tmp_path):
    # A QA agent once made a .venv inside its output dir; 11k library files filled the judge
    # prompt and the real report was never shown.
    (tmp_path / "QA-REPORT.md").write_text("verdict: PASS", encoding="utf-8")
    for d in (".venv/Lib/site-packages/dateutil", "node_modules/x", "sub/__pycache__", "venv/Lib"):
        (tmp_path / d).mkdir(parents=True)
        for i in range(25):
            (tmp_path / d / f"m{i}.py").write_text("import sys", encoding="utf-8")
    (tmp_path / "sub" / "notes.md").write_text("kept", encoding="utf-8")
    assert [p.name for p in checks.output_files(str(tmp_path))] == ["QA-REPORT.md", "notes.md"]
    assert "verdict: PASS" in checks.read_output(str(tmp_path))


def test_output_files_keep_deliverables_in_dot_dirs(tmp_path):
    # A GitHub Actions workflow lives in .github/; skipping every dot-directory hid the deliverable.
    # Venvs are recognised by pyvenv.cfg whatever their name (a QA agent made one called cleanvenv).
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push", encoding="utf-8")
    for d in (".git/objects", ".pytest_cache/v", "cleanvenv/Scripts"):
        (tmp_path / d).mkdir(parents=True)
        (tmp_path / d / "x.py").write_text("junk", encoding="utf-8")
    (tmp_path / "cleanvenv" / "pyvenv.cfg").write_text("home = C:\\Python", encoding="utf-8")
    assert [p.name for p in checks.output_files(str(tmp_path))] == ["ci.yml"]
    assert "on: push" in checks.read_output(str(tmp_path))


def test_parse_judge_json_tolerates_fences_and_chatter():
    assert judge.parse_judge_json(_reply(0.5, 0.5, fence=True))["correctness"] == 0.5
    assert judge.parse_judge_json("no json here") is None
    assert judge.parse_judge_json('{"a": {"b": 1}} trailing')["a"]["b"] == 1


def test_ensemble_scoring_fitness_and_idempotency(evolvra_home, recorder, monkeypatch):
    for env in ("GROQ_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(env, "k")
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder)
    ingest.ingest_all(conn, evolvra_home)
    transport = judge_transport({
        "openai/gpt-oss-120b": _reply(0.9, 0.8),
        "gemini-3.5-flash-lite": _reply(0.7, 0.6, fc="generic_copy", fence=True),
        "qwen/qwen3.8-27b": _reply(0.8, 0.7, fc="generic_copy"),
    })
    tasks = runner.pending_tasks(conn)
    report = runner.score_tasks(conn, tasks, JUDGES, _transport=transport)
    assert report.tasks_scored == 1 and report.judge_calls == 3 and report.judge_errors == 0

    ens = {r["metric"]: r["value"] for r in conn.execute(
        "SELECT metric, value FROM scores WHERE judge_model = 'ensemble'")}
    # trimmed-low mean: the single most lenient judge is dropped, the rest averaged
    assert ens["rubric:correctness"] == 0.75 and ens["rubric:quality"] == 0.65
    fc = conn.execute("SELECT json_extract(evidence_json,'$.failure_class') FROM scores"
                      " WHERE judge_model='ensemble' AND metric='rubric:correctness'").fetchone()[0]
    assert fc == "generic_copy"  # majority of judges

    f = fitness.task_fitness(conn, tasks[0]["id"])
    expected = (0.35 * 0.75 + 0.15 * 0.9 + 0.15 * 0.65 + 0.10 * 0.8 + 0.10 * 1 + 0.10 * 1 + 0.05 * 1)
    assert abs(f - round(expected, 4)) < 1e-6
    rows = fitness.agent_fitness(conn)
    assert rows[0]["agent"] == "content-creator" and rows[0]["version"] == 1
    assert rows[0]["top_failure"] == "generic_copy"

    # second pass: nothing pending, and a forced rescore hits the cache instead of the network
    assert runner.pending_tasks(conn) == []
    report2 = runner.score_tasks(conn, runner.pending_tasks(conn, rescore=True), JUDGES, _transport=transport)
    assert report2.judge_cached == 3 and len(transport.calls) == 3
    assert conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0] == 4 + 3 * 4 + 4  # det + 3 judges + ensemble


def test_aggregate_trims_lenient_judge_and_surfaces_strictest_critique():
    def jr(name, c, e, fc, crit):
        return judge.JudgeResult(name, {"correctness": c, "completeness": 1.0, "quality": 1.0, "evidence": e},
                                 [], crit, fc, False, "")
    results = [jr("lenient-a", 1.0, 1.0, "none", "none"), jr("lenient-b", 1.0, 1.0, "none", "none"),
               jr("strict", 0.4, 0.2, "fabricated_evidence", "invents command output")]
    scores, failure, critique = judge.aggregate(results)
    assert scores["correctness"] == 0.7 and scores["evidence"] == 0.6   # mean of the two lowest
    assert failure == "fabricated_evidence" and critique == "invents command output"
    two = judge.aggregate(results[1:])
    assert two[0]["correctness"] == 0.7                                   # 2 judges: plain mean
    assert judge.trimmed_low_mean([]) == 0.0 and judge.trimmed_low_mean([0.5]) == 0.5


def test_qa_efficiency_ignores_retries_caused_by_builder(evolvra_home, recorder):
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    recorder("start", "--brief", "Fair QA", "--mode", "micro")
    mid = max((evolvra_home / "missions").iterdir()).name
    recorder("task", "add", mid, "--agent", "content-creator", "--task", "Write")
    recorder("task", "add", mid, "--agent", "evidence-collector", "--task", "Verify", "--depends", "1")
    recorder("task", "start", mid, "1"); recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "v1")
    recorder("task", "start", mid, "2"); recorder("task", "done", mid, "2", "--verdict", "NEEDS_WORK", "--feedback", "too long")
    recorder("task", "start", mid, "1"); recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "v2")
    recorder("task", "start", mid, "2"); recorder("task", "done", mid, "2", "--verdict", "PASS", "--evidence", "ok")
    recorder("finish", mid, "--status", "done")
    ingest.ingest_all(conn, evolvra_home)
    tasks = {t["agent_slug"]: t for t in runner.pending_tasks(conn)}
    builder = {m: v for m, v, _ in checks.run_checks(tasks["content-creator"])}
    qa = {m: v for m, v, _ in checks.run_checks(tasks["evidence-collector"])}
    assert tasks["content-creator"]["attempts"] == 2 and builder["det:efficiency"] == 0.5   # builder pays
    assert tasks["evidence-collector"]["attempts"] == 2 and qa["det:efficiency"] == 1.0       # QA does not


def test_judge_error_does_not_break_scoring(evolvra_home, recorder, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)  # gemini judges will fail: no key
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder, with_output=False)
    ingest.ingest_all(conn, evolvra_home)
    transport = judge_transport({"openai/gpt-oss-120b": _reply(0.4, 0.4, fc="missing_output")})
    judges = [("groq", "openai/gpt-oss-120b"), ("gemini", "gemini-3.5-flash-lite"), ("gemini", "gemma-4-31b-it")]
    report = runner.score_tasks(conn, runner.pending_tasks(conn), judges, _transport=transport)
    assert report.judge_errors == 2 and report.tasks_scored == 1
    ens = {r["metric"]: r["value"] for r in conn.execute("SELECT metric, value FROM scores WHERE judge_model='ensemble'")}
    assert ens["rubric:correctness"] == 0.4  # single valid judge still yields an ensemble
    det = conn.execute("SELECT value FROM scores WHERE metric='det:output_exists'").fetchone()[0]
    assert det == 0.0


def test_unparseable_judge_gets_one_strict_retry(evolvra_home, recorder, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder)
    ingest.ingest_all(conn, evolvra_home)
    calls = []

    def transport(url, body, api_key, timeout):
        calls.append(body)
        text = "Sure! Here is my assessment in prose." if len(calls) == 1 else _reply(0.6, 0.6)
        return {"choices": [{"message": {"content": text}, "finish_reason": "stop"}], "usage": {}}

    report = runner.score_tasks(conn, runner.pending_tasks(conn), [("groq", "openai/gpt-oss-120b")], _transport=transport)
    assert report.judge_errors == 0 and len(calls) == 2
    assert "ONLY the JSON" in calls[1]["messages"][-1]["content"]
