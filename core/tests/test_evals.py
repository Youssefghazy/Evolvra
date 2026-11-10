import json
from pathlib import Path

from evolvra.evals import checks, fitness, judge, runner
from evolvra.missions import ingest
from evolvra.registry import personas
from evolvra.router import client
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
    # ceiling-aware: no two judges at the ceiling here, so the median (0.9/0.7/0.8 -> 0.8; 0.8/0.6/0.7 -> 0.7)
    assert ens["rubric:correctness"] == 0.8 and ens["rubric:quality"] == 0.7
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
    # genuine disagreement with only one judge at the ceiling: median, so one wrong low judge cannot sink it
    assert judge.ceiling_aware([1.0, 0.68, 0.5]) == 0.68
    assert judge.ceiling_aware([1.0, 1.0, 0.4]) == 0.7
    assert judge.ceiling_aware([0.9, 0.6]) == 0.75


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
    assert ens["rubric:correctness"] == 0.4  # single valid judge still yields an ensemble row
    det = conn.execute("SELECT value FROM scores WHERE metric='det:output_exists'").fetchone()[0]
    assert det == 0.0
    task_id = conn.execute("SELECT id FROM tasks").fetchone()[0]
    assert fitness.task_fitness(conn, task_id) is None                 # provisional: one judge is not enough
    assert fitness.task_fitness(conn, task_id, min_judges=1) is not None


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


def test_judge_that_runs_out_of_budget_gets_a_bigger_one(evolvra_home, recorder, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder)
    ingest.ingest_all(conn, evolvra_home)
    calls = []

    def transport(url, body, api_key, timeout):
        calls.append(body)
        if body["max_tokens"] <= 900:
            return {"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {}}
        return {"choices": [{"message": {"content": _reply(0.6, 0.6)}, "finish_reason": "stop"}], "usage": {}}

    report = runner.score_tasks(conn, runner.pending_tasks(conn), [("groq", "qwen/qwen3.8-27b")], _transport=transport)
    assert report.judge_errors == 0
    assert [c["max_tokens"] for c in calls[:2]] == [900, judge.RETRY_MAX_TOKENS]


def test_truncated_judge_json_is_not_read_as_zero_scores(evolvra_home, recorder, monkeypatch):
    # A reply cut off mid-JSON still contains a complete inner object (one acceptance item). Reading
    # that as the verdict gave 0.0 on every metric, and the trimmed mean averaged the zeros in.
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder)
    ingest.ingest_all(conn, evolvra_home)
    cut = _reply(0.7, 0.7)[:80]
    assert judge.parse_judge_json(cut) and "correctness" not in judge.parse_judge_json(cut)

    def transport(url, body, api_key, timeout):
        if body["max_tokens"] <= 900:
            return {"choices": [{"message": {"content": cut}, "finish_reason": "length"}], "usage": {}}
        return {"choices": [{"message": {"content": _reply(0.7, 0.7)}, "finish_reason": "stop"}], "usage": {}}

    results = judge.judge_prompt(conn, "grade this", [("gemini", "gemini-3.5-flash-lite")], _transport=transport)
    assert results[0].scores["correctness"] == 0.7


def test_read_output_prefers_main_deliverable_and_shows_tail(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    guide = "# Guide\n" + ("intro line\n" * 600) + "## Main questions\n1. Why did you stop?\n"
    (out / "GUIDE.md").write_text(guide, encoding="utf-8")
    (out / "notes.md").write_text("short notes", encoding="utf-8")
    (out / "GUIDE.attempt1.md").write_text("STALE DRAFT " * 500, encoding="utf-8")
    text = checks.read_output(str(out), per_file=500, total=9000, primary_chars=6000)
    assert text.index("GUIDE.md") < text.index("notes.md")          # largest text file first
    assert "## Main questions" in text and "characters omitted" in text  # tail survives the cut
    assert "STALE DRAFT" not in text                                   # backups skipped
    assert checks.excerpt("abc", 10) == "abc"


def test_thin_ensemble_is_rescored_next_cycle(evolvra_home, recorder, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder)
    ingest.ingest_all(conn, evolvra_home)
    one_judge = [("groq", "openai/gpt-oss-120b")]
    transport = judge_transport({"openai/gpt-oss-120b": _reply(0.7, 0.7)})
    runner.score_tasks(conn, runner.pending_tasks(conn), one_judge, _transport=transport)
    assert len(runner.pending_tasks(conn)) == 1          # only one judge answered: still pending
    three = [("groq", "openai/gpt-oss-120b"), ("groq", "qwen/qwen3.8-27b")]
    transport2 = judge_transport({"openai/gpt-oss-120b": _reply(0.7, 0.7), "qwen/qwen3.8-27b": _reply(0.6, 0.6)})
    rep = runner.score_tasks(conn, runner.pending_tasks(conn), three, _transport=transport2)
    assert rep.judge_cached == 1 and runner.pending_tasks(conn) == []   # cached first judge, now complete
    body = transport2.calls[0]
    assert body["model"] == "qwen/qwen3.8-27b" and body["reasoning_effort"] == "none"


def test_rescore_keeps_the_better_covered_ensemble(evolvra_home, recorder, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder)
    ingest.ingest_all(conn, evolvra_home)
    three = [("groq", "openai/gpt-oss-120b"), ("gemini", "gemini-3.5-flash-lite"), ("groq", "qwen/qwen3.8-27b")]
    full = judge_transport({"openai/gpt-oss-120b": _reply(0.6, 0.6), "gemini-3.5-flash-lite": _reply(0.7, 0.7),
                            "qwen/qwen3.8-27b": _reply(0.8, 0.8)})
    runner.score_tasks(conn, runner.pending_tasks(conn), three, _transport=full)
    task_id = conn.execute("SELECT id FROM tasks").fetchone()[0]
    before = fitness.task_fitness(conn, task_id)
    assert judge.ensemble_judges(conn, task_id) == 3 and before is not None

    def capped(url, body, api_key, timeout):           # Groq at its daily cap: only Gemini answers
        if "gemini" in body["model"]:
            return full(url, body, api_key, timeout)
        raise client.ProviderError("HTTP 429 from provider: daily cap")

    runner.score_tasks(conn, runner.pending_tasks(conn, rescore=True), three, _transport=capped)
    assert judge.ensemble_judges(conn, task_id) == 3 and fitness.task_fitness(conn, task_id) == before


def test_measured_facts_count_words_and_paragraphs(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    para = " ".join(["word"] * 104)
    (out / "ANNOUNCEMENT.md").write_text(f"# Title\n\n{para}\n\n{para}\n\n- a list item\n\n{para}\n", encoding="utf-8")
    facts = checks.measured_facts(str(out), ["exactly 3 paragraphs, each 90-110 words"])
    assert "3 prose paragraphs" in facts and "[104, 104, 104]" in facts
    assert checks.measured_facts(str(out), ["mentions offline sync"]) == ""     # no count criterion, no block
    prompt = judge.render_prompt(brief="b", agent="a", agent_description="d", task="t", criteria=["90-110 words"],
                                 attempts=1, verdict="PASS", evidence="e", output="o", facts=facts)
    assert "# Measured facts" in prompt and "never report a count violation" in prompt


def test_prompt_numbers_criteria_and_judges_answer_by_id():
    prompt = judge.render_prompt(brief="b", agent="a", agent_description="d", task="t",
                                 criteria=["the text names exactly two product features", "3 paragraphs"],
                                 attempts=1, verdict="PASS", evidence="e", output="o")
    assert "C1. the text names exactly two product features" in prompt and "C2. 3 paragraphs" in prompt
    assert '"id": "C1"' in prompt and "not each paragraph" in prompt
    crit = ["the text names exactly two product features", "3 paragraphs"]
    got = judge.normalize_acceptance([
        {"id": "C2", "met": True, "reason": "3"},                                   # by id
        {"index": 1, "met": True, "reason": "two"},                                 # by index
        {"criterion": "3 Paragraphs ", "met": True, "reason": "ok"},                # older prompt: verbatim text
        {"criterion": "Each paragraph names exactly two product features", "met": False, "reason": "p1 none"},
        "junk",
    ], crit)
    assert [g.get("id") for g in got] == ["C2", "C1", "C2", None]
    assert got[1]["criterion"] == crit[0] and got[2]["criterion"] == crit[1]
    assert got[3]["rewritten"] is True and "rewritten" not in got[0]
    assert judge.normalize_acceptance("not a list", crit) == []


def _jr(name, c, fc="none", crit="none"):
    return judge.JudgeResult(name, {"correctness": c, "completeness": 1.0, "quality": 1.0, "evidence": c},
                             [], crit, fc, False, "")


def test_lone_failure_class_is_kept_but_labelled_contested():
    # the announcement case of 2026-11-05: one judge misreads a criterion, two find every criterion met
    lone = judge.aggregate_detail([_jr("groq/gpt-oss", 0.4, "missing_feature_mentions"),
                                   _jr("openrouter/nemotron", 1.0), _jr("gemini/flash-lite", 1.0)])
    assert lone["failure_class"] == "missing_feature_mentions" and lone["contested_by"] == "groq/gpt-oss"
    assert lone["scores"]["correctness"] == 0.7                       # the score rule is unchanged
    # a second judge raising any failure, or a second judge below the ceiling, makes it a real finding
    shared = judge.aggregate_detail([_jr("a", 0.4, "x"), _jr("b", 0.8, "y"), _jr("c", 1.0)])
    split = judge.aggregate_detail([_jr("a", 0.4, "x"), _jr("b", 0.8), _jr("c", 1.0)])
    assert shared["contested_by"] is None and split["contested_by"] is None
    assert judge.aggregate([_jr("a", 0.4, "x"), _jr("b", 1.0), _jr("c", 1.0)])[1] == "x"   # old API intact


def test_reaggregate_applies_new_rules_without_calls_and_errors_are_kept(evolvra_home, recorder, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    _recorded_mission(evolvra_home, recorder)
    ingest.ingest_all(conn, evolvra_home)
    three = [("groq", "openai/gpt-oss-120b"), ("gemini", "gemini-3.5-flash-lite"), ("groq", "qwen/qwen3.8-27b")]
    replies = {"openai/gpt-oss-120b": _reply(0.4, 0.5, fc="generic_copy"),
               "gemini-3.5-flash-lite": _reply(1.0, 1.0), "qwen/qwen3.8-27b": _reply(1.0, 1.0)}
    runner.score_tasks(conn, runner.pending_tasks(conn), three, _transport=judge_transport(replies))
    tid = conn.execute("SELECT id FROM tasks").fetchone()[0]
    sql = ("SELECT evidence_json FROM scores WHERE task_id=? AND judge_model='ensemble' AND metric='rubric:correctness'")
    ev = json.loads(conn.execute(sql, (tid,)).fetchone()[0])
    assert ev["contested_by"] == "groq/openai/gpt-oss-120b"
    # simulate an ensemble written before the rule existed, then rebuild it from the stored judge rows
    del ev["contested_by"]
    conn.execute("UPDATE scores SET evidence_json=? WHERE task_id=? AND judge_model='ensemble'", (json.dumps(ev), tid))
    assert judge.reaggregate(conn, tid) is True
    assert json.loads(conn.execute(sql, (tid,)).fetchone()[0])["contested_by"] == "groq/openai/gpt-oss-120b"
    row = fitness.agent_fitness(conn)[0]
    assert row["top_failure"] == "generic_copy" and row["top_failure_contested"] is True

    def capped(url, body, api_key, timeout):            # a capped day: the guard keeps the 3-judge ensemble...
        if "gemini" in body["model"]:
            return judge_transport(replies)(url, body, api_key, timeout)
        raise client.ProviderError("HTTP 429 from provider: daily cap")

    conn.execute("DELETE FROM llm_cache")              # force real (failing) calls instead of cache hits
    runner.score_tasks(conn, runner.pending_tasks(conn, rescore=True), three, _transport=capped)
    errors = conn.execute("SELECT COUNT(*) FROM scores WHERE task_id=? AND metric='rubric:error'", (tid,)).fetchone()[0]
    assert judge.ensemble_judges(conn, tid) == 3 and errors == 2      # ...and still records why two judges missed


def test_nemotron_gets_the_large_budget_first_and_no_second_request():
    sent = []

    def t(url, body, api_key, timeout):
        sent.append(body["max_tokens"])
        return {"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {"total_tokens": 9}}

    import os
    os.environ.setdefault("OPENROUTER_API_KEY", "k")
    conn = db.connect(":memory:")
    res = judge.judge_prompt(conn, "p", [("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free")], _transport=t)
    assert sent[0] == judge.RETRY_MAX_TOKENS          # no 900-token attempt to throw away
    assert sent.count(judge.RETRY_MAX_TOKENS) == len(sent) and len(sent) <= 2   # at most the JSON-repair retry
    assert res[0].failure_class == "judge_unparseable"


def test_judges_see_the_files_the_agent_cites_first_with_their_paths(tmp_path):
    out = tmp_path / "02-evidence-collector"
    (out / "scratch").mkdir(parents=True)
    (out / "evidence").mkdir()
    (out / "scratch" / "harness.ps1").write_text("x" * 30000, encoding="utf-8")          # big, unmentioned
    for i in range(30):                                                                     # more than the old cap
        (out / "scratch" / f"fixture-{i:02d}.log").write_text("f" * 500, encoding="utf-8")
    (out / "evidence" / "selftest.txt").write_text("SelfTest 13/13 PASS exit 0", encoding="utf-8")
    (out / "QA-REPORT.md").write_text("# QA report\nverdict PASS", encoding="utf-8")
    text = checks.read_output(str(out), mentions="See evidence\\selftest.txt and QA-REPORT.md")
    assert text.index("--- evidence/selftest.txt") < text.index("--- scratch/harness.ps1")
    assert "SelfTest 13/13 PASS" in text and "--- QA-REPORT.md" in text
    assert "do not report this part as missing" in checks.excerpt("y" * 50, 20)


def test_qa_proof_beats_a_copy_of_the_builders_code(tmp_path):
    out = tmp_path / "02-evidence-collector"
    for d in ("work", "evidence"):
        (out / d).mkdir(parents=True)
    (out / "work" / "notes_api.py").write_text("code " * 4000, encoding="utf-8")         # copy of the builder's file
    (out / "independent_check.py").write_text("check " * 1500, encoding="utf-8")
    for i in range(11):
        (out / "evidence" / f"check-{i:02d}.txt").write_text(f"check {i}: PASS " * 20, encoding="utf-8")
    for name in ("stdout.txt", "stderr.txt", "exit.txt"):
        (out / "evidence" / name).write_text("", encoding="utf-8")                          # empty captures
    text = checks.read_output(str(out), mentions="ran independent_check.py against notes_api.py; see evidence/")
    assert text.startswith("--- independent_check.py")                 # main deliverable: the QA's own script
    assert all(f"--- evidence/check-{i:02d}.txt" in text for i in range(11))
    assert "stderr.txt" not in text                                    # empty files are not listed
    assert "work/notes_api.py" not in text or text.index("work/notes_api.py") > text.index("evidence/check-10.txt")


def test_a_long_qa_report_leaves_room_for_its_proof(tmp_path):
    out = tmp_path / "02-evidence-collector"
    (out / "evidence").mkdir(parents=True)
    (out / "QA-REPORT.md").write_text("finding " * 1500, encoding="utf-8")                  # ~12k chars
    for i in range(20):
        (out / "evidence" / f"{i:02d}-check.txt").write_text(f"check {i}: PASS exit 0 " * 60, encoding="utf-8")
    (out / "evidence" / "run1.txt.stdout").write_bytes(b"")                                 # empty, odd suffix
    text = checks.read_output(str(out), mentions="see QA-REPORT.md and evidence/")
    assert text.startswith("--- QA-REPORT.md")
    shown = sum(f"--- evidence/{i:02d}-check.txt" in text for i in range(20))
    assert shown >= 10                                   # most proof files get an excerpt (was 1 of 20)
    assert "run1.txt.stdout" not in text                 # 0-byte files are skipped whatever their suffix
    assert len(text) < 17500                             # still inside the judge budget
    if shown < 20:
        assert "they exist; do not report them as missing" in text


def test_thousands_of_fixtures_cannot_hide_the_report(tmp_path):
    out = tmp_path / "01-reality-checker"
    (out / "fx").mkdir(parents=True)
    (out / "evidence").mkdir()
    for i in range(1200):                                                # an unrecognised bulk folder
        (out / "fx" / f"file-{i:04d}.txt").write_text("fixture data " * 10, encoding="utf-8")
    (out / "evidence" / "stress.txt").write_text("2000 files in 12 s; flip detected", encoding="utf-8")
    (out / "REALITY-CHECK.md").write_text("Verdict: NEEDS WORK\n" + "detail " * 300, encoding="utf-8")
    text = checks.read_output(str(out), mentions="wrote REALITY-CHECK.md; evidence/ holds the ledger")
    assert text.startswith("--- REALITY-CHECK.md") and "--- evidence/stress.txt" in text
    shown_fx = [line for line in text.splitlines() if line.startswith("--- fx/")]
    assert len(shown_fx) <= checks.LOW_SAMPLES and "fx/ (" in text       # a few examples, the rest summarised
    assert len(text) <= 16000 + 200                                     # headers now count toward the budget


def test_a_qa_mutant_is_never_shown_as_the_subject(tmp_path):
    out = tmp_path / "02-evidence-collector"
    for d in ("mutants", "evidence", "logs"):
        (out / d).mkdir(parents=True)
    (out / "mutants" / "m2-missing-exit-5.ps1").write_text("exit 5 # deliberately broken\n" * 400, encoding="utf-8")
    (out / "QA-REPORT.md").write_text("# QA\nPASS; mutant m2 was caught\n" * 20, encoding="utf-8")
    (out / "evidence" / "exitcodes.txt").write_text("missing file -> exit 2 (expected 2)", encoding="utf-8")
    (out / "logs" / "app.log").write_text("2026-11-10 ERROR boom\n" * 50, encoding="utf-8")
    (out / "notes.env").write_text("GROQ_API_KEY=should-never-reach-a-judge", encoding="utf-8")
    text = checks.read_output(str(out), mentions="see QA-REPORT.md and evidence/exitcodes.txt; mutants in mutants/")
    assert text.startswith("--- QA-REPORT.md")
    assert text.index("--- evidence/exitcodes.txt") < text.index("mutants/")
    assert "--- logs/app.log" in text and "(binary" not in text        # .log is text now
    assert "notes.env" not in text and "should-never" not in text      # secret-like files are never read or listed
