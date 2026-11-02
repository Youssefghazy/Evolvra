# Mission record format (schema 1)

Written by `plugin/scripts/mission.py`, read by `evolvra ingest`. One directory per mission:

```
$EVOLVRA_HOME/                      (default ~/.evolvra)
├── current.json                    pointer to the running mission/task; read by the trace hook
├── traces.jsonl                    one JSON line per Claude Code hook event
└── missions/<id>/
    ├── mission.json                the record below
    ├── 01-<agent-slug>/            output files of task 1
    └── 02-<agent-slug>/
```

`<id>` = `YYYYMMDD-HHMMSS-<first four words of the brief>` (UTC).

## mission.json

```json
{
  "schema": 1,
  "id": "20261102-120755-write-a-one-paragraph",
  "brief": "write a one paragraph product description for a note-taking app",
  "mode": "micro",                      // micro | sprint | full
  "status": "done",                     // running | done | failed | escalated
  "started_at": "2026-11-02T12:07:55Z",
  "finished_at": "2026-11-02T12:09:10Z",
  "summary": "Paragraph delivered.",
  "tasks": [
    {
      "no": 1,
      "agent": "content-creator",       // slug from plugin/agents/MANIFEST.json
      "task": "Write the paragraph",
      "acceptance": ["Under 120 words", "Mentions sync"],
      "depends_on": [],
      "status": "done",                 // pending | running | done | escalated
      "output_dir": ".../01-content-creator",
      "attempts": [
        {"n": 1, "started_at": "...", "finished_at": "...", "verdict": "FAIL",
         "feedback": "too long", "evidence": null},
        {"n": 2, "started_at": "...", "finished_at": "...", "verdict": "PASS",
         "feedback": null, "evidence": "118 words, mentions sync"}
      ]
    }
  ]
}
```

Rules enforced by the recorder: a task cannot start until its dependencies are `done`; a task gets at most
**3 attempts**, after which it becomes `escalated`; verdicts are `PASS`, `FAIL` or `NEEDS_WORK`.

## traces.jsonl

```json
{"ts": "2026-11-02T12:08:01+0000", "mission": "20261102-120755-write-a-one-paragraph", "task_no": 1,
 "event": "PostToolUse", "session_id": "...", "tool_name": "Write",
 "tool_input": {"file_path": "..."}, "tool_response": "...", "agent": null, "transcript_path": "..."}
```

Large fields are truncated to 4000 characters; full outputs live in the task's `output_dir`.
`mission` and `task_no` come from `current.json`, so events outside a mission carry `null`.

## Ingestion

`evolvra ingest` upserts missions by `id` and tasks by `(mission, no)`, links each task to the agent's
current registry version, and appends new trace lines (tracked by line number). Running it twice changes nothing.
Invalid files are listed on stderr and skipped, never crash the run.
