import json
from pathlib import Path

from evolvra.evals import checks, fitness, judge, runner
from evolvra.missions import ingest
from evolvra.registry import personas
from evolvra.store import db

from .conftest import mission_id

AGENTS_DIR = Path(__file__).resolve().parents[2] / "plugin" / "agents"
JUDGES = [("groq", "openai/gpt-oss-120b"), ("gemini", "gemini-3.5-flash-lite"), ("gemini", "gemma-4-31b-it")]


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
        "gemma-4-31b-it": _reply(0.8, 0.7, fc="generic_copy"),
    })
    tasks = runner.pending_tasks(conn)
    report = runner.score_tasks(conn, tasks, JUDGES, _transport=transport)
    assert report.tasks_scored == 1 and report.judge_calls == 3 and report.judge_errors == 0

    ens = {r["metric"]: r["value"] for r in conn.execute(
        "SELECT metric, value FROM scores WHERE judge_model = 'ensemble'")}
    assert ens["rubric:correctness"] == 0.8 and ens["rubric:quality"] == 0.7  # medians
    fc = conn.execute("SELECT json_extract(evidence_json,'$.failure_class') FROM scores"
                      " WHERE judge_model='ensemble' AND metric='rubric:correctness'").fetchone()[0]
    assert fc == "generic_copy"  # majority of judges

    f = fitness.task_fitness(conn, tasks[0]["id"])
    expected = (0.35 * 0.8 + 0.15 * 0.9 + 0.15 * 0.7 + 0.10 * 0.8 + 0.10 * 1 + 0.10 * 1 + 0.05 * 1)
    assert abs(f - round(expected, 4)) < 1e-6
    rows = fitness.agent_fitness(conn)
    assert rows[0]["agent"] == "content-creator" and rows[0]["version"] == 1
    assert rows[0]["top_failure"] == "generic_copy"

    # second pass: nothing pending, and a forced rescore hits the cache instead of the network
    assert runner.pending_tasks(conn) == []
    report2 = runner.score_tasks(conn, runner.pending_tasks(conn, rescore=True), JUDGES, _transport=transport)
    assert report2.judge_cached == 3 and len(transport.calls) == 3
    assert conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0] == 4 + 3 * 4 + 4  # det + 3 judges + ensemble


def test_judge_error_does_not_break_scoring(evolvra_home, recorder, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)  # gemini judges will fail: no key
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder, with_output=False)
    ingest.ingest_all(conn, evolvra_home)
    transport = judge_transport({"openai/gpt-oss-120b": _reply(0.4, 0.4, fc="missing_output")})
    report = runner.score_tasks(conn, runner.pending_tasks(conn), JUDGES, _transport=transport)
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
