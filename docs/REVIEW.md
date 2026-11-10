# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-10, after STATUS `b475949` (round 14)._

## Verdict
- The devops QA task improved (0.5 → 0.75 ensemble) and Nemotron parses again. gpt-oss's remaining point (no
  per-criterion verdict in a file) is fair, and item 2 below fixes the cause.
- Asking the ux QA agent for a top-level `QA-REPORT.md` worked; it is now standard.
- ux-researcher 0.955 over 2 tasks. QA's 3 findings (2 surviving mutants, a cp1252 crash, an unreachable prompt)
  are good catches.

## Fixed (tests 75, ruff clean, plugin 0.3.8)
1. **Judge input for QA folders** (your open question 1):
   - A **top-level report file** (name contains report/verdict/findings; .md/.txt/.html) is now the main file, ahead
     of the script that produced it.
   - Files named like **transcript / results / outputs / expected-vs-actual / exitcodes** count as proof, even outside
     `evidence/`.
   - **Superseded first runs** (`run1`, `run-1`, `first-run`, `old-`) rank with scratch: at most 3 examples, after
     everything else.
   - A top-level omitted file is now named correctly (it was shown as if it were a folder).
   - Tested with your frontend layout: report, then transcript, then driver.
2. **Mission skill handoff** (your open question 2): QA agents now also write `QA-REPORT.md` at the top of their
   output folder, with the verdict on line 1 and one line per criterion (verified / not verified / failed) plus the
   proving file. Plugin 0.3.8.

## Requested now (short round)
1. `git pull`, tests: **expect 75**, ruff clean, plugin update to **0.3.8**, fresh session.
2. Re-score the frontend mission (its input changes now; 3 calls):
   `uv run evolvra score --mission 20261110-051125-build-a-single-file --rescore`. Report the QA task per judge.
3. One mission for **sprint-prioritizer** or **content-creator** (your open question 3). Check that its QA agent
   writes `QA-REPORT.md` without being asked by hand.
4. `.\scripts\cycle.ps1` (no `-Evolve`), outside :15–:50. Short STATUS with `-- docs/STATUS.md`.
