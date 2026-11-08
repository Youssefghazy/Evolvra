# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-08, after STATUS `2714c33` (round 10)._

## Verdict
- **DevOps Automator v2, first real task: 0.974** (v1: 0.881 over 4 tasks). The builder's own honesty notes
  (not run on GitHub, tags not checked online) are exactly what we want. One task is not a trend; keep going.
- Your offline rebuild of the judge input found the real cause of "missing evidence": the budget, not the order.

## Fixed this round (tests 72, ruff clean, plugin 0.3.6)
1. **Empty files of any suffix are skipped** (your open question 1). `.stdout` and `.stderr` captures no longer show
   as "(binary, 0 bytes)".
2. **QA proof budget** (your open question 2):
   - When proof files exist, the main file is capped at ~35% of the 16k budget, and the proof files share most of
     the rest.
   - A file that does not fit whole still gets an excerpt instead of stopping the list.
   - Files left out are **named**, with "they exist; do not report them as missing".
   - On a layout like your devops QA task (12k report plus 20 proofs), proofs with content go from 1 to 14, and the
     other 6 are named.
3. **gpt-oss as the lone dissenter:** no new rule. When the other two judges are at 1.0 with no failure, its class is
   already labelled `contested` (so it does not steer evolution), and its score still counts by design. Let's see
   whether fix 2 removes the cause before changing the judge seat.
4. **Bank task from QA's findings** (your open question 3): yes. devops-automator's bank has a 4th held-out task: a
   CI checker that proves the test step is real (commented out / `if: false` / echoed, case-sensitive events and
   actions, misspelled keys, a self-test with 6 or more targeted broken samples). It is self-contained and passes
   the bank filters.

## Requested now (short round)
1. `git pull`, tests: **expect 72**, ruff clean. Plugin update to **0.3.6** (only the bank changed; personas
   unchanged), then a fresh session.
2. Re-score the two QA-heavy missions with the new budget (about 12 calls, Groq permitting):
   - `uv run evolvra score --mission 20261108-064726-build-a-small-stdlib --rescore`
   - `uv run evolvra score --mission 20261108-080705-devops-build-a-github --rescore`
   Report the QA tasks per judge, before and after, and rebuild the judge input once to confirm how many
   `evidence/` files now show.
3. Keep confirming v2: one devops-automator mission per day, varied (a backup verifier, a log parser with a
   summary report, a scheduled-task XML generator), built-ins only.
4. Vary the roster: also one mission today for an agent with few tasks (frontend-developer: 1, ux-researcher: 1,
   reality-checker: 0).
5. `.\scripts\cycle.ps1` (no `-Evolve`; outside :15–:50 past 04/10/16/22). STATUS with `-- docs/STATUS.md`.
