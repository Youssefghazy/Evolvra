#!/usr/bin/env python3
"""Evolvra mission recorder. Standard library only. Called by the /evolvra:mission skill.

Writes one directory per mission under $EVOLVRA_HOME/missions/<id>/ with a mission.json
that the core ingests later. Also maintains $EVOLVRA_HOME/current.json so the trace hook
can tag every tool call with the mission and task it belongs to.

Usage (see `python mission.py -h`):
  start   --brief TEXT --mode micro|sprint|full
  task add   ID --agent SLUG --task TEXT [--acceptance TEXT ...] [--depends N,N]
  task start ID NO
  task done  ID NO --verdict PASS|FAIL|NEEDS_WORK [--feedback TEXT] [--evidence TEXT] [--output-dir PATH]
  finish  ID --status done|failed|escalated [--summary TEXT]
  show    ID
  current
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SCHEMA = 1
MAX_ATTEMPTS = 3
VERDICTS = ("PASS", "FAIL", "NEEDS_WORK")
MODES = ("micro", "sprint", "full")
FINAL = ("done", "failed", "escalated")


def home() -> Path:
    h = os.environ.get("EVOLVRA_HOME")
    p = Path(h).expanduser() if h else Path.home() / ".evolvra"
    (p / "missions").mkdir(parents=True, exist_ok=True)
    return p


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def slugify(text: str, words: int = 4) -> str:
    parts = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    return "-".join(parts[:words]) or "mission"


def mission_dir(mid: str) -> Path:
    return home() / "missions" / mid


def load(mid: str) -> dict:
    path = mission_dir(mid) / "mission.json"
    if not path.exists():
        sys.exit(f"error: no mission '{mid}' at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save(m: dict) -> None:
    d = mission_dir(m["id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "mission.json.tmp"
    tmp.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, d / "mission.json")  # atomic on every OS


def set_current(mid: str | None, task_no: int | None = None) -> None:
    path = home() / "current.json"
    if mid is None:
        if path.exists():
            path.unlink()
        return
    path.write_text(json.dumps({"mission": mid, "task_no": task_no, "updated_at": now()}), encoding="utf-8")


def get_task(m: dict, no: int) -> dict:
    for t in m["tasks"]:
        if t["no"] == no:
            return t
    sys.exit(f"error: mission {m['id']} has no task {no}")


# ---- commands -------------------------------------------------------------

def cmd_start(a) -> int:
    mid = f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{slugify(a.brief)}"
    m = {
        "schema": SCHEMA, "id": mid, "brief": a.brief, "mode": a.mode, "status": "running",
        "started_at": now(), "finished_at": None, "summary": None, "tasks": [],
    }
    save(m)
    set_current(mid)
    print(json.dumps({"id": mid, "dir": str(mission_dir(mid))}))
    return 0


def cmd_task_add(a) -> int:
    m = load(a.id)
    no = len(m["tasks"]) + 1
    depends = [int(x) for x in a.depends.split(",") if x.strip()] if a.depends else []
    for d in depends:
        if d < 1 or d >= no:
            sys.exit(f"error: task {no} cannot depend on task {d}")
    m["tasks"].append({
        "no": no, "agent": a.agent, "task": a.task, "acceptance": a.acceptance or [],
        "depends_on": depends, "status": "pending", "attempts": [], "output_dir": None,
    })
    save(m)
    print(json.dumps({"id": m["id"], "task_no": no, "output_dir": str(mission_dir(m["id"]) / f"{no:02d}-{a.agent}")}))
    return 0


def cmd_task_start(a) -> int:
    m = load(a.id)
    t = get_task(m, a.no)
    if t["status"] == "done":
        sys.exit(f"error: task {a.no} is already done")
    if len(t["attempts"]) >= MAX_ATTEMPTS:
        sys.exit(f"error: task {a.no} already used {MAX_ATTEMPTS} attempts; escalate instead")
    for d in t["depends_on"]:
        if get_task(m, d)["status"] != "done":
            sys.exit(f"error: task {a.no} depends on task {d}, which is not done")
    t["status"] = "running"
    t["attempts"].append({"n": len(t["attempts"]) + 1, "started_at": now(), "finished_at": None,
                          "verdict": None, "feedback": None, "evidence": None})
    out = mission_dir(m["id"]) / f"{t['no']:02d}-{t['agent']}"
    out.mkdir(parents=True, exist_ok=True)
    t["output_dir"] = str(out)
    save(m)
    set_current(m["id"], t["no"])
    print(json.dumps({"id": m["id"], "task_no": t["no"], "attempt": len(t["attempts"]), "output_dir": str(out)}))
    return 0


def cmd_task_done(a) -> int:
    m = load(a.id)
    t = get_task(m, a.no)
    if t["status"] != "running" or not t["attempts"]:
        sys.exit(f"error: task {a.no} is not running; call `task start` first")
    att = t["attempts"][-1]
    att.update({"finished_at": now(), "verdict": a.verdict, "feedback": a.feedback, "evidence": a.evidence})
    if a.output_dir:
        t["output_dir"] = a.output_dir
    if a.verdict == "PASS":
        t["status"] = "done"
    elif len(t["attempts"]) >= MAX_ATTEMPTS:
        t["status"] = "escalated"
    else:
        t["status"] = "pending"  # retry with feedback
    save(m)
    set_current(m["id"], None)
    print(json.dumps({"id": m["id"], "task_no": t["no"], "status": t["status"],
                      "attempts_used": len(t["attempts"]), "attempts_left": MAX_ATTEMPTS - len(t["attempts"])}))
    return 0


def cmd_finish(a) -> int:
    m = load(a.id)
    m["status"] = a.status
    m["finished_at"] = now()
    m["summary"] = a.summary
    save(m)
    set_current(None)
    done = sum(t["status"] == "done" for t in m["tasks"])
    print(json.dumps({"id": m["id"], "status": a.status, "tasks": len(m["tasks"]), "tasks_done": done}))
    return 0


def cmd_show(a) -> int:
    print(json.dumps(load(a.id), indent=2, ensure_ascii=False))
    return 0


def cmd_current(_a) -> int:
    path = home() / "current.json"
    print(path.read_text(encoding="utf-8").strip() if path.exists() else "null")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mission.py", description="Evolvra mission recorder")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start"); s.add_argument("--brief", required=True); s.add_argument("--mode", choices=MODES, default="micro")
    s.set_defaults(fn=cmd_start)

    task = sub.add_parser("task").add_subparsers(dest="tcmd", required=True)
    s = task.add_parser("add"); s.add_argument("id"); s.add_argument("--agent", required=True)
    s.add_argument("--task", required=True); s.add_argument("--acceptance", action="append"); s.add_argument("--depends")
    s.set_defaults(fn=cmd_task_add)
    s = task.add_parser("start"); s.add_argument("id"); s.add_argument("no", type=int); s.set_defaults(fn=cmd_task_start)
    s = task.add_parser("done"); s.add_argument("id"); s.add_argument("no", type=int)
    s.add_argument("--verdict", required=True, choices=VERDICTS); s.add_argument("--feedback"); s.add_argument("--evidence")
    s.add_argument("--output-dir"); s.set_defaults(fn=cmd_task_done)

    s = sub.add_parser("finish"); s.add_argument("id"); s.add_argument("--status", required=True, choices=FINAL)
    s.add_argument("--summary"); s.set_defaults(fn=cmd_finish)
    s = sub.add_parser("show"); s.add_argument("id"); s.set_defaults(fn=cmd_show)
    sub.add_parser("current").set_defaults(fn=cmd_current)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
