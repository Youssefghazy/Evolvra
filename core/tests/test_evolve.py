import json
import shutil
from pathlib import Path

from evolvra.evals import judge
from evolvra.evolve import bank, diagnose, engine, mutate, tournament
from evolvra.registry import personas
from evolvra.router import client
from evolvra.store import db

REPO = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO / "plugin" / "agents"
JUDGES = [("groq", "openai/gpt-oss-120b"), ("gemini", "gemini-3.5-flash-lite")]
ACTOR = ("groq", "openai/gpt-oss-120b")


def _plugin_copy(tmp_path) -> Path:
    """A throwaway repo layout: <root>/.claude-plugin/marketplace.json, <root>/plugin/{.claude-plugin,agents}."""
    root = tmp_path / "repo"
    shutil.copytree(AGENTS_DIR, root / "plugin" / "agents")
    shutil.copytree(REPO / "plugin" / ".claude-plugin", root / "plugin" / ".claude-plugin")
    shutil.copytree(REPO / ".claude-plugin", root / ".claude-plugin")
    return root / "plugin" / "agents"


def _judge_reply(c):
    return json.dumps({"acceptance": [], "correctness": c, "completeness": c, "quality": c, "evidence": c,
                       "critique": "ok" if c > 0.7 else "weak evidence", "failure_class": "none" if c > 0.7 else "weak_evidence"})


def make_transport(persona_scores: dict[str, float], mutations: dict[int, str]):
    """Fake provider: the actor echoes a marker from the persona; judges score by that marker."""
    calls = []
    state = {"mutations": 0}

    def _t(url, body, api_key, timeout):
        calls.append(body)
        system = body["messages"][0]["content"]
        user = body["messages"][-1]["content"]
        if "senior prompt engineer" in system:                      # mutator
            state["mutations"] += 1
            return _reply(mutations[state["mutations"]])
        if "QA reviewer" in system:                                 # judge: find marker in output
            marker = next((m for m in persona_scores if f"MARKER:{m}" in user), "parent")
            return _reply(_judge_reply(persona_scores[marker]))
        marker = next((m for m in persona_scores if f"MARKER:{m}" in system), "parent")  # actor
        return _reply(f"Deliverable by {marker}. MARKER:{marker}\n\n## Evidence\nAll criteria addressed.")

    def _reply(text):
        return {"choices": [{"message": {"content": text}, "finish_reason": "stop"}], "usage": {"total_tokens": 10}}

    _t.calls = calls
    return _t


def _variant(base: str, marker: str, extra: str = "") -> str:
    return base.rstrip() + f"\n\n## Evolved Rule\nAlways state evidence. MARKER:{marker}\n{extra}"


def test_bank_merges_missions_and_seeds(evolvra_home, recorder):
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    tasks = bank.load_bank(conn, AGENTS_DIR, "content-creator")
    assert len(tasks) == 3 and all(t.source == "seed" for t in tasks)
    assert bank.load_bank(conn, AGENTS_DIR, "content-creator", size=2)[0].acceptance


def test_bank_excludes_dependent_and_file_bound_mission_tasks(evolvra_home, recorder):
    from evolvra.missions import ingest
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    recorder("start", "--brief", "Bank hygiene", "--mode", "micro")
    mid = max((evolvra_home / "missions").iterdir()).name
    recorder("task", "add", mid, "--agent", "evidence-collector", "--task", "Define the QA evidence standard")
    recorder("task", "add", mid, "--agent", "evidence-collector", "--task", "Verify description.md", "--depends", "1")
    recorder("task", "add", mid, "--agent", "evidence-collector", "--task", "Check the report.json output")
    for no in (1, 2, 3):
        recorder("task", "start", mid, str(no))
        recorder("task", "done", mid, str(no), "--verdict", "PASS", "--evidence", "ok")
    ingest.ingest_all(conn, evolvra_home)
    mission_only = [t for t in bank.load_bank(conn, AGENTS_DIR, "evidence-collector") if t.source != "seed"]
    assert [t.task for t in mission_only] == ["Define the QA evidence standard"]   # task 2 had no materials
    assert bank.is_self_contained("Write a checklist", ["3 items"], []) is True


def test_dependent_qa_task_enters_bank_with_builder_output_embedded(evolvra_home, recorder):
    from evolvra.missions import ingest
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    recorder("start", "--brief", "Note app launch", "--mode", "micro")
    mid = max((evolvra_home / "missions").iterdir()).name
    recorder("task", "add", mid, "--agent", "content-creator", "--task", "Write description.md")
    recorder("task", "add", mid, "--agent", "evidence-collector", "--task", "Verify description.md against the criteria",
             "--acceptance", "Reports word count", "--depends", "1")
    recorder("task", "start", mid, "1")
    out = evolvra_home / "missions" / mid / "01-content-creator"
    (out / "description.md").write_text("Inkwell keeps notes in sync. " * 8, encoding="utf-8")
    recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "written")
    recorder("task", "start", mid, "2"); recorder("task", "done", mid, "2", "--verdict", "PASS", "--evidence", "ok")
    ingest.ingest_all(conn, evolvra_home)
    tasks = bank.load_bank(conn, AGENTS_DIR, "evidence-collector")
    embedded = [t for t in tasks if "materials embedded" in t.source]
    assert len(embedded) == 1 and "Inkwell keeps notes in sync" in embedded[0].brief
    assert "## Input materials" in embedded[0].brief and embedded[0].task.startswith("Verify description.md")


def test_pick_targets_fills_with_generic():
    d = diagnose.Diagnosis("x", 1, 2, 0.5, [("generic_copy", 2)], [])
    assert mutate.pick_targets(d, 3) == ["generic_copy", "weak_evidence", "missing_acceptance_criteria_check"]


def test_split_evidence_and_proxy_fitness():
    body, ev = tournament.split_evidence("work\n\n## Evidence\nproof")
    assert body == "work" and ev == "proof"
    assert tournament.proxy_fitness({"correctness": 1, "completeness": 1, "quality": 1, "evidence": 1}) == 1.0
    assert tournament.proxy_fitness({}) is None


def test_evolve_promotes_only_a_winner(tmp_path, evolvra_home, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    plugin = _plugin_copy(tmp_path)
    conn = db.connect(":memory:")
    personas.import_dir(conn, plugin)
    base = (plugin / "marketing-content-creator.md").read_text(encoding="utf-8")
    transport = make_transport(
        {"parent": 0.6, "c1": 0.62, "c2": 0.9, "c3": 0.5},
        {1: _variant(base, "c1"), 2: _variant(base, "c2"), 3: "---\nname: Broken\n---\nshort"},
    )
    opts = engine.EvolveOptions(candidates=3, bank_size=2, margin=0.03, actor=ACTOR, judges=JUDGES, mutator=ACTOR)
    res = engine.evolve(conn, "content-creator", plugin, opts, home=evolvra_home, _transport=transport)

    assert res.parent_fitness == 0.6 and res.winner_index == 2 and res.new_version == 2
    assert abs(res.delta - 0.3) < 1e-6 and res.coverage == 2
    assert res.candidates[2]["lint_ok"] is False  # broken candidate filtered, never played
    assert "MARKER:c2" in (plugin / "marketing-content-creator.md").read_text(encoding="utf-8")
    manifest = json.loads((plugin / "MANIFEST.json").read_text(encoding="utf-8"))
    entry = next(a for a in manifest["agents"] if a["slug"] == "content-creator")
    assert entry["version"] == 2 and entry["parent"] == 1 and entry["history"][0]["rationale"].startswith("evolved")
    lineage = personas.lineage(conn, "content-creator")
    assert [r["version"] for r in lineage] == [1, 2] and lineage[1]["created_by"] == "evolve"
    evo = conn.execute("SELECT winner_version, bank_delta FROM evolutions").fetchone()
    assert evo["winner_version"] == 2 and abs(evo["bank_delta"] - 0.3) < 1e-6
    # the promotion ships itself: plugin + marketplace versions are patch-bumped
    before = json.loads((REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text())["version"]
    after = json.loads((plugin.parent / ".claude-plugin" / "plugin.json").read_text())["version"]
    market = json.loads((plugin.parents[1] / ".claude-plugin" / "marketplace.json").read_text())
    assert after != before and after.split(".")[:2] == before.split(".")[:2]
    assert market["plugins"][0]["version"] == after and market["metadata"]["version"] == after
    assert (res.evolution_dir / "report.md").exists() and (res.evolution_dir / "diagnosis.md").exists()
    assert (res.evolution_dir / "arena" / "parent" / "task-1.md").exists()
    assert (res.evolution_dir / "arena" / "candidate-2" / "task-2.md").read_text(encoding="utf-8").count("MARKER:c2") == 1
    assert res.candidates[1]["per_task"][0]["output_excerpt"].startswith("Deliverable by c2")
    # calls: 3 mutations + (parent + 2 valid candidates) * 2 tasks * (1 actor + 2 judges)
    assert len(transport.calls) == 3 + 3 * 2 * 3


def test_evolve_archives_when_no_candidate_beats_parent(tmp_path, evolvra_home, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    plugin = _plugin_copy(tmp_path)
    conn = db.connect(":memory:")
    personas.import_dir(conn, plugin)
    base = (plugin / "testing-reality-checker.md").read_text(encoding="utf-8")
    before = base
    transport = make_transport({"parent": 0.8, "c1": 0.81}, {1: _variant(base, "c1")})
    opts = engine.EvolveOptions(candidates=1, bank_size=1, margin=0.03, actor=ACTOR, judges=JUDGES, mutator=ACTOR)
    res = engine.evolve(conn, "reality-checker", plugin, opts, home=evolvra_home, _transport=transport)
    assert res.winner_index is None and res.new_version is None
    assert (plugin / "testing-reality-checker.md").read_text(encoding="utf-8") == before
    assert conn.execute("SELECT winner_version FROM evolutions").fetchone()[0] is None
    assert [r["version"] for r in personas.lineage(conn, "reality-checker")] == [1]


def test_evolve_dry_run_makes_no_calls(tmp_path, evolvra_home):
    plugin = _plugin_copy(tmp_path)
    conn = db.connect(":memory:")
    personas.import_dir(conn, plugin)
    transport = make_transport({"parent": 0.5}, {})
    res = engine.evolve(conn, "growth-hacker", plugin, engine.EvolveOptions(dry_run=True), home=evolvra_home,
                        _transport=transport)
    assert res.dry_run and res.bank_size == 3 and len(res.candidates) == 3 and transport.calls == []


def test_judge_prompt_render_is_used_by_tournament():
    text = judge.render_prompt(brief="b", agent="a", agent_description="d", task="t", criteria=["c1"],
                               attempts=1, verdict="PASS", evidence="e", output="o")
    assert "C1. c1" in text and "# Output files\no" in text


def test_paired_delta_only_counts_shared_tasks():
    from evolvra.evolve.bank import BankTask
    t1, t2, t3 = (BankTask("b", f"task {i}", (), "seed") for i in range(3))
    parent = tournament.PersonaResult("parent", [tournament.TaskResult(t1, "", {}, 0.5, "none", "", 0),
                                                 tournament.TaskResult(t2, "", {}, 0.6, "none", "", 0),
                                                 tournament.TaskResult(t3, "", {}, None, "actor_error", "", 0)])
    cand = tournament.PersonaResult("c", [tournament.TaskResult(t1, "", {}, 0.9, "none", "", 0),
                                          tournament.TaskResult(t2, "", {}, None, "actor_error", "", 0),
                                          tournament.TaskResult(t3, "", {}, 1.0, "none", "", 0)])
    delta, shared = tournament.paired_delta(cand, parent)
    assert shared == 1 and abs(delta - 0.4) < 1e-9   # only task 1 is shared; task 3's 1.0 does not count


def test_low_coverage_candidate_is_not_promoted(tmp_path, evolvra_home, monkeypatch):
    """A candidate that scores 1.0 on the few tasks it finished must not win on coverage luck."""
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    plugin = _plugin_copy(tmp_path)
    conn = db.connect(":memory:")
    personas.import_dir(conn, plugin)
    base = (plugin / "marketing-growth-hacker.md").read_text(encoding="utf-8")
    inner = make_transport({"parent": 0.6, "c1": 1.0}, {1: _variant(base, "c1")})
    seen = {"c1_actor": 0}

    def flaky(url, body, api_key, timeout):
        system = body["messages"][0]["content"]
        if "MARKER:c1" in system and "QA reviewer" not in system:   # candidate's actor calls
            seen["c1_actor"] += 1
            if seen["c1_actor"] <= 2:                                 # first two tasks: rate limited
                raise client.ProviderError("HTTP 429 from provider: rate limit")
        return inner(url, body, api_key, timeout)

    opts = engine.EvolveOptions(candidates=1, bank_size=3, margin=0.03, actor=ACTOR, judges=JUDGES, mutator=ACTOR)
    res = engine.evolve(conn, "growth-hacker", plugin, opts, home=evolvra_home, _transport=flaky)
    assert res.winner_index is None and res.candidates[0]["shared_tasks"] == 1
    assert "MARKER:c1" not in (plugin / "marketing-growth-hacker.md").read_text(encoding="utf-8")


def test_bank_drops_tasks_that_require_execution():
    assert bank.requires_execution("Write a CI workflow", ["actionlint reports 0 errors", "pytest passes"]) is True
    assert bank.requires_execution("Write an interview guide", ["5 open questions", "under 45 minutes"]) is False
    conn = db.connect(":memory:")
    personas.import_dir(conn, AGENTS_DIR)
    devops = bank.load_bank(conn, AGENTS_DIR, "devops-automator")
    assert all(not bank.requires_execution(t.task, list(t.acceptance)) for t in devops)


def test_unchanged_generation_is_refused_as_replay(tmp_path, evolvra_home, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    plugin = _plugin_copy(tmp_path)
    conn = db.connect(":memory:")
    personas.import_dir(conn, plugin)
    base = (plugin / "testing-reality-checker.md").read_text(encoding="utf-8")
    transport = make_transport({"parent": 0.8, "c1": 0.81}, {1: _variant(base, "c1"), 2: _variant(base, "c1")})
    opts = engine.EvolveOptions(candidates=1, bank_size=1, margin=0.03, actor=ACTOR, judges=JUDGES, mutator=ACTOR)
    engine.evolve(conn, "reality-checker", plugin, opts, home=evolvra_home, _transport=transport)
    import pytest
    with pytest.raises(engine.ReplayError):
        engine.evolve(conn, "reality-checker", plugin, opts, home=evolvra_home, _transport=transport)
    assert conn.execute("SELECT COUNT(*) FROM evolutions").fetchone()[0] == 1


def test_rewrite_too_large_for_groq_falls_back_to_gemini(monkeypatch):
    import os

    from evolvra.evolve import diagnose, mutate
    from evolvra.router import client
    from evolvra.store import db
    os.environ.setdefault("GROQ_API_KEY", "k")
    os.environ.setdefault("GEMINI_API_KEY", "k")
    persona = (AGENTS_DIR / "engineering-devops-automator.md").read_text(encoding="utf-8")
    calls = []

    def t(url, body, api_key, timeout):
        calls.append(body["model"])
        if body["model"] == "openai/gpt-oss-120b":
            raise client.ProviderError('HTTP 413 from provider: {"error":{"message":"Request too large for model"}}')
        return {"choices": [{"message": {"content": persona}, "finish_reason": "stop"}], "usage": {"total_tokens": 9}}

    diag = diagnose.Diagnosis("devops-automator", 1, 3, 0.87, [("invalid_yaml_syntax", 1)], [])
    cands = mutate.propose(db.connect(":memory:"), persona, diag, k=1, _transport=t)
    assert calls == ["openai/gpt-oss-120b", "gemini-3.5-flash-lite"]
    assert cands[0].content and cands[0].author == "gemini/gemini-3.5-flash-lite" and not cands[0].problems

    def other(url, body, api_key, timeout):            # any other provider error is not retried elsewhere
        raise client.ProviderError("HTTP 500 from provider: boom")
    c2 = mutate.propose(db.connect(":memory:"), persona, diag, k=1, _transport=other)
    assert c2[0].problems and "HTTP 500" in c2[0].problems[0]


def test_plugin_hook_runs_without_a_shell():
    import json
    hooks = json.loads((AGENTS_DIR.parent / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    for event in hooks.values():
        for h in event[0]["hooks"]:
            assert h["command"] == "python" and h["args"] == ["${CLAUDE_PLUGIN_ROOT}/hooks/log_event.py"]
            assert not any(tok in h["command"] for tok in ("if ", "then", ";", "&&", "|"))


def test_generation_that_lost_rewrites_to_errors_may_run_again(tmp_path, evolvra_home, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    plugin = _plugin_copy(tmp_path)
    conn = db.connect(":memory:")
    personas.import_dir(conn, plugin)
    base = (plugin / "testing-reality-checker.md").read_text(encoding="utf-8")
    inner = make_transport({"parent": 0.8, "c1": 0.81}, {1: _variant(base, "c1"), 2: _variant(base, "c1")})
    state = {"failed": False}

    def flaky(url, body, api_key, timeout):            # the first rewrite request fails at the provider
        if not state["failed"] and "prompt engineer" in json.dumps(body["messages"][0]):
            state["failed"] = True
            raise client.ProviderError("HTTP 503 from provider: overloaded")
        return inner(url, body, api_key, timeout)

    opts = engine.EvolveOptions(candidates=1, bank_size=1, margin=0.03, actor=ACTOR, judges=JUDGES, mutator=ACTOR)
    first = engine.evolve(conn, "reality-checker", plugin, opts, home=evolvra_home, _transport=flaky)
    assert "mutator error" in first.candidates[0]["problems"][0]
    engine.evolve(conn, "reality-checker", plugin, opts, home=evolvra_home, _transport=flaky)   # not a replay
    assert conn.execute("SELECT COUNT(*) FROM evolutions").fetchone()[0] == 2
