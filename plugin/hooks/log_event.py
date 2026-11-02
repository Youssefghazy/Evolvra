#!/usr/bin/env python3
"""Evolvra hook: append one JSON line per Claude Code hook event.

Reads the hook payload from stdin, trims large fields, and appends to
$EVOLVRA_HOME/traces.jsonl (default ~/.evolvra). Standard library only.
Never raises: a logging failure must never break a Claude Code session.
"""
import json
import os
import sys
import time

MAX_FIELD = 4000  # chars kept per large field; full outputs live in mission dirs


def _trim(value):
    if isinstance(value, str) and len(value) > MAX_FIELD:
        return value[:MAX_FIELD] + f"... [truncated {len(value) - MAX_FIELD} chars]"
    if isinstance(value, dict):
        return {k: _trim(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_trim(v) for v in value[:50]]
    return value


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        home = os.environ.get("EVOLVRA_HOME") or os.path.join(os.path.expanduser("~"), ".evolvra")
        os.makedirs(home, exist_ok=True)
        event = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "event": payload.get("hook_event_name"),
            "session_id": payload.get("session_id"),
            "cwd": payload.get("cwd"),
            "tool_name": payload.get("tool_name"),
            "tool_input": _trim(payload.get("tool_input")),
            "tool_response": _trim(payload.get("tool_response")),
            "agent": payload.get("agent_type") or payload.get("subagent_type"),
            "transcript_path": payload.get("transcript_path"),
        }
        with open(os.path.join(home, "traces.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — logging must never break the session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
