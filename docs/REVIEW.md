# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-03, after STATUS session 11:42–12:40 AST._

## Verdict on your last session
Excellent. Every REVIEW item done, two real engine bugs found and fixed with tests first, and the arena audit
was the most valuable finding of the project so far: **the ensemble could not reward improvement** (two lenient
judges at 1.0, median aggregation, easy seed-only bank). I have acted on all of it (commit on `main` after
`6e5a44c`):

- judges: Gemma dropped; `qwen/qwen3.8-27b` (Groq) added; three lineages
- aggregation: median → trimmed-low mean (drop the single most lenient score per metric); critique and
  failure class now come from the strictest judge that found a problem; calibration anchors in the prompt
- bank: dependent QA tasks now enter the bank with the builder's output embedded inline ("Input materials")
- recorder: `task done <qa> --verdict FAIL|NEEDS_WORK` auto-reopens the builder dependencies; QA re-runs
  caused by a builder fix carry `caused_by_builder` and do not reduce QA's `det:efficiency`; `note` command
- hook: `off_record: true` on SubagentStop while a mission is active but no task is running
- skill: never resume an agent after a QA failure, relaunch via `task start`; no "run a command" criteria
  for agents without a shell tool (that goes to QA)
- plugin bumped to **0.3.0**

Answers to your open questions: (1) done as above; (2) done; (3) no longer counts against QA; (4) keep shell
off those personas, route execution criteria to QA (skill updated); (5) `note` exists now, use it to annotate
mission 3 without editing attempts.

## Requested now (priority order)
1. `git pull`, then refresh the plugin to 0.3.0 (`claude plugin marketplace update evolvra`,
   `claude plugin update evolvra@evolvra`), and ask Youssef to restart Claude Code. Confirm in STATUS.md.
2. **Re-score everything with the new ensemble**: `cd core; uv run evolvra score --rescore` (cached calls for
   the two kept judges; Qwen is new, expect ~1 call per task). Then `uv run evolvra fitness`. Report the
   before/after fitness per agent: the point is to see scores come off the 1.0 ceiling.
3. Check `uv run evolvra bank evidence-collector` now shows mission-derived tasks "(materials embedded)".
4. Run **one** evolution: `.\scripts\cycle.ps1 -Evolve`. Report parent fitness, paired deltas, coverage,
   whether a promotion happened, wall-clock, and provider counts. If the parent still sits at 1.0 on every
   bank task, say so plainly: that means the actor (Flash-Lite) saturates and we must move the actor to a
   weaker or stricter setting, which I will decide.
5. Annotate mission 3: `python plugin/scripts/mission.py note <id> --task 1 --text "<the sequence you wrote>"`.
6. Run two missions on untouched agents: pick `rapid-prototyper` (single-file HTML mock with 3 measurable
   criteria) and `ux-researcher` (interview guide, 5 open questions, recruiting criterion). If a QA failure
   happens naturally, let the new reopen flow run; do not force one.
7. Do not change weights, judge sets, margins or the actor without writing the reason in STATUS.md first.

## Open questions for the local operator
- Does Qwen on Groq hit the 8k TPM cap together with gpt-oss? Watch for 429 waits in the score output.
- After the restart, does `/evolvra:mission` print `"reopened": [..]` on a QA failure? (needs a real one)
