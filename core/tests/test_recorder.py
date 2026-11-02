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
