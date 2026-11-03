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
    dst = tmp_path / "plugin-agents"
    shutil.copytree(AGENTS_DIR, dst)
    return dst


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
    assert [t.task for t in mission_only] == ["Define the QA evidence standard"]
    assert bank.is_self_contained("Write a checklist", ["3 items"], []) is True


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
    assert "- c1" in text and "# Output files\no" in text


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
