# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-10, after STATUS `d59426d` (round 16)._

## Verdict
- Frontend QA 0.655 → 0.855. gpt-oss now accepts the evidence; its only point (no per-criterion report) is fair
  for a pre-0.3.8 QA run.
- QA-REPORT.md was written unprompted again (rapid-prototyper, 5,198 scenarios, 0 failures, plus a negative
  control). The template works.
- Evidence Collector v2: 0.939 over 17 tasks (v1 0.872 over 8).

## Decisions
1. **Scorer tuning stops here** (your open question 1). The remaining gap is one transcript shown at ~25% in one
   legacy folder; new QA runs write QA-REPORT.md, which leads the judge input. More tuning would change little and
   cost re-score calls.
2. Agreed on your open question 2: re-score only when the judge input changes.

## Steady state from now on (no new engineering requests)
The project is feature-complete. Each working day:
1. `git pull`, tests (**expect 76**).
2. **Two missions**, rotating agents with the fewest tasks: backend-architect, content-creator, growth-hacker,
   ux-researcher and frontend-developer first, plus a devops-automator v2 task every few days.
3. `.\scripts\cycle.ps1` (no `-Evolve`; the scheduled run evolves while the PC is awake). Short STATUS with the
   pathspec. Raise only real problems; I will review when STATUS changes.
