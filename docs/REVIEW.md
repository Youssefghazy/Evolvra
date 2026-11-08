# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-08 ~08:30Z, after STATUS `9401d15` (round 9)._

## Verdict
**Second promotion: DevOps Automator v1 → v2** (generation 12, +5.75 points on held-out tasks; the gate is +3).
It is the first generation in which all 3 rewrites played. Two of the three were written by the new Gemini
fallback, so the weekend fixes paid off immediately.
- Caveat, stated honestly in the README: the win rests on **2 shared held-out tasks**, the minimum coverage the
  rules accept. Real missions decide it, as they did for Evidence Collector v2 (item 3).
- Rebuilding the exact judge input offline to prove the backend QA failure was a scorer issue was excellent work.

## Fixed this round (tests 71, ruff clean, plugin 0.3.5)
1. **Version bump left behind after a promotion.**
   - The cycle now commits `plugin/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` together with
     `plugin/agents`.
   - I committed the 0.3.4 → 0.3.5 bump myself (the same value the engine wrote on your PC). Your uncommitted copy is
     identical, so `git pull --rebase --autostash` applies cleanly.
2. **A rejected push exited 0.** `evolvra cycle` now returns 1 when the push fails, and `cycle.ps1` ends with that
   code. A failed push therefore shows as a non-zero "Last Run Result" in Task Scheduler. The retry pull uses
   `--autostash`, so the 10:27 case (blocked by those unstaged version files) would now have succeeded.
3. **Judge file order for QA tasks:**
   - **Main deliverable first:** the largest non-scratch file the evidence statement mentions; for QA this is its
     own check script or report.
   - **Then proof files:** anything under `evidence/` (or `proof`, `results`, `logs`, `captures`, `outputs`), or
     mentioned by its relative path.
   - **Then other named files**, then the rest, with `work/`, `scratch/`, `fixtures/`, `copy/` last.
   - **Empty files are not listed**, so no more "all evidence files are empty".
   - Tested with your exact layout: copy of `notes_api.py` in `work/`, `independent_check.py`, 11 proofs, 3 empty
     captures.
4. **Candidate author** is now saved in each candidate entry (`author`: Groq or the Gemini fallback), in the DB
   and in result.json.

## Requested now (short round)
1. `git pull` (with autostash), tests: **expect 71**, ruff clean. Refresh the plugin to **0.3.5**
   (`claude plugin marketplace update evolvra`, `claude plugin update evolvra@evolvra`) and start a fresh session.
   This is what delivers **devops-automator v2** to missions; check that the cached persona file is the v2 one.
2. Re-score the backend mission with the fixed order (6 calls):
   `uv run evolvra score --mission 20261108-064726-build-a-small-stdlib --rescore`.
   Report whether the QA task's "missing evidence" is gone.
3. **Confirm v2 on real work:** one devops-automator mission now (on v2), and more on later days. A different
   kind of task from the last two (for example a scheduled-task XML or a CI workflow YAML, built-ins only, with
   `-WhatIf`/self-test where it applies). After 3 or more v2 tasks, compare v2 vs v1 real fitness, as we did for
   Evidence Collector.
4. `.\scripts\cycle.ps1` (no `-Evolve`; outside :15–:50 past 04/10/16/22). STATUS with `-- docs/STATUS.md`.
