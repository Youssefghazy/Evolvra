import json

import pytest

from .conftest import mission_id


def test_full_mission_flow_with_retry_and_dependency(evolvra_home, recorder, capsys):
    assert recorder("start", "--brief", "Write a product paragraph", "--mode", "micro") == 0
    mid = mission_id(evolvra_home)
    assert mid.endswith("-write-a-product-paragraph")
    assert json.loads((evolvra_home / "current.json").read_text())["mission"] == mid

    recorder("task", "add", mid, "--agent", "content-creator", "--task", "Write it",
             "--acceptance", "under 120 words", "--acceptance", "mentions sync")
    recorder("task", "add", mid, "--agent", "evidence-collector", "--task", "Verify", "--depends", "1")

    with pytest.raises(SystemExit):  # dependency not done yet
        recorder("task", "start", mid, "2")

    recorder("task", "start", mid, "1")
    assert json.loads((evolvra_home / "current.json").read_text())["task_no"] == 1
    recorder("task", "done", mid, "1", "--verdict", "FAIL", "--feedback", "too long")
    capsys.readouterr()
    recorder("task", "start", mid, "1")
    recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "118 words")
    recorder("task", "start", mid, "2")
    recorder("task", "done", mid, "2", "--verdict", "PASS", "--evidence", "checked")
    recorder("finish", mid, "--status", "done", "--summary", "Delivered.")

    m = json.loads((evolvra_home / "missions" / mid / "mission.json").read_text())
    assert m["status"] == "done" and m["summary"] == "Delivered."
    t1, t2 = m["tasks"]
    assert t1["status"] == "done" and len(t1["attempts"]) == 2
    assert t1["attempts"][0]["verdict"] == "FAIL" and t1["attempts"][0]["feedback"] == "too long"
    assert t1["acceptance"] == ["under 120 words", "mentions sync"]
    assert t2["depends_on"] == [1] and t2["status"] == "done"
    assert (evolvra_home / "missions" / mid / "01-content-creator").is_dir()
    assert not (evolvra_home / "current.json").exists()


def test_three_failures_escalate(evolvra_home, recorder, capsys):
    recorder("start", "--brief", "Hard task")
    mid = mission_id(evolvra_home)
    recorder("task", "add", mid, "--agent", "rapid-prototyper", "--task", "Do it")
    for _ in range(3):
        recorder("task", "start", mid, "1")
        recorder("task", "done", mid, "1", "--verdict", "FAIL", "--feedback", "nope")
    m = json.loads((evolvra_home / "missions" / mid / "mission.json").read_text())
    assert m["tasks"][0]["status"] == "escalated"
    with pytest.raises(SystemExit):
        recorder("task", "start", mid, "1")


def test_hook_tags_events_with_current_mission(evolvra_home, recorder, hook):
    recorder("start", "--brief", "Tag me")
    mid = mission_id(evolvra_home)
    recorder("task", "add", mid, "--agent", "frontend-developer", "--task", "x")
    recorder("task", "start", mid, "1")
    hook({"hook_event_name": "PostToolUse", "session_id": "s", "tool_name": "Write",
          "tool_input": {"file_path": "a"}, "tool_response": "x" * 5000})
    recorder("finish", mid, "--status", "done")
    hook({"hook_event_name": "PostToolUse", "session_id": "s", "tool_name": "Bash"})

    lines = [json.loads(x) for x in (evolvra_home / "traces.jsonl").read_text().splitlines()]
    assert lines[0]["mission"] == mid and lines[0]["task_no"] == 1
    assert "truncated" in lines[0]["tool_response"]
    assert lines[1]["mission"] is None  # mission finished, pointer cleared


def test_reopen_flips_builder_attempt_and_resets_dependants(evolvra_home, recorder):
    recorder("start", "--brief", "Reopen me")
    mid = mission_id(evolvra_home)
    recorder("task", "add", mid, "--agent", "growth-hacker", "--task", "Plan")
    recorder("task", "add", mid, "--agent", "evidence-collector", "--task", "Verify", "--depends", "1")
    recorder("task", "start", mid, "1")
    recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "written")
    recorder("task", "start", mid, "2")
    recorder("task", "done", mid, "2", "--verdict", "PASS", "--evidence", "looked fine")   # premature
    recorder("task", "reopen", mid, "1", "--feedback", "sample sizes wrong")
    m = json.loads((evolvra_home / "missions" / mid / "mission.json").read_text())
    t1, t2 = m["tasks"]
    assert t1["status"] == "pending" and t1["attempts"][-1]["verdict"] == "FAIL"
    assert t1["attempts"][-1]["feedback"] == "sample sizes wrong" and t1["attempts"][-1]["reopened_by_qa"]
    assert t2["status"] == "pending"  # QA must run again against the fixed work
    recorder("task", "start", mid, "1")
    recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "fixed")
    m = json.loads((evolvra_home / "missions" / mid / "mission.json").read_text())
    assert len(m["tasks"][0]["attempts"]) == 2 and m["tasks"][0]["status"] == "done"


def test_qa_failure_auto_reopens_builder_and_marks_caused_retry(evolvra_home, recorder, capsys):
    recorder("start", "--brief", "Auto reopen")
    mid = mission_id(evolvra_home)
    recorder("task", "add", mid, "--agent", "growth-hacker", "--task", "Plan")
    recorder("task", "add", mid, "--agent", "evidence-collector", "--task", "Verify", "--depends", "1")
    recorder("task", "start", mid, "1"); recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "x")
    recorder("task", "start", mid, "2")
    capsys.readouterr()
    recorder("task", "done", mid, "2", "--verdict", "NEEDS_WORK", "--feedback", "stats wrong")
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["reopened"] == [1] and out["status"] == "pending"
    m = json.loads((evolvra_home / "missions" / mid / "mission.json").read_text())
    t1, t2 = m["tasks"]
    assert t1["status"] == "pending" and t1["attempts"][-1]["verdict"] == "FAIL"
    assert t1["attempts"][-1]["feedback"] == "stats wrong" and t1["attempts"][-1]["reopened_by_qa"]
    assert t2["attempts"][-1]["verdict"] == "NEEDS_WORK"
    with pytest.raises(SystemExit):           # QA cannot restart before the builder redoes the work
        recorder("task", "start", mid, "2")
    recorder("task", "start", mid, "1"); recorder("task", "done", mid, "1", "--verdict", "PASS", "--evidence", "y")
    recorder("task", "start", mid, "2")
    m = json.loads((evolvra_home / "missions" / mid / "mission.json").read_text())
    assert m["tasks"][1]["attempts"][-1]["caused_by_builder"] is True
    recorder("note", mid, "--text", "builder resumed off-record in an old tab", "--task", "1")
    m = json.loads((evolvra_home / "missions" / mid / "mission.json").read_text())
    assert m["notes"][0]["task_no"] == 1 and m["tasks"][0]["attempts"][-1]["verdict"] == "PASS"


def test_hook_flags_off_record_subagent_work(evolvra_home, recorder, hook):
    recorder("start", "--brief", "Off record")
    hook({"hook_event_name": "SubagentStop", "session_id": "s"})          # mission active, no task running
    hook({"hook_event_name": "PostToolUse", "session_id": "s", "tool_name": "Read"})
    lines = [json.loads(x) for x in (evolvra_home / "traces.jsonl").read_text().splitlines()]
    assert lines[0]["off_record"] is True and lines[1]["off_record"] is False
