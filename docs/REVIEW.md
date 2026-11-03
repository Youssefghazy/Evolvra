# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-03._

## Verdict on the last 24h
Phases 0–4 are complete and CI is green. Three real missions ran today with strong QA behaviour (QA wrote its
own checkers and mutation-tested them). Two evolution generations ran: the first was spoiled by Groq rate
limits, the second was clean but unfair because a mission-derived bank task referenced a file the arena
actor could not see. Both causes are fixed (`ac13dc5` and earlier).

## Requested now (priority order)
1. **Finish mission 3** (growth experiments) through the Dev↔QA loop. If QA fails the builder, use
   `mission.py task reopen` (new) so the retry is recorded. Finish with the honest status.
2. **Run `.\scripts\cycle.ps1 -Evolve`** once mission 3 is finished, and report in STATUS.md: parent fitness,
   each candidate's paired delta and coverage, whether a promotion happened, and the provider request counts.
3. **Audit one arena task by hand.** Open `~/.evolvra/evolutions/<latest>/arena/parent/task-1.md` and one
   candidate's `task-1.md`. Do the judges' critiques match what you see? Note any judge bias in STATUS.md.
4. **Run two more missions** that use agents with no data yet: `frontend-developer` (a small component with
   accessibility criteria) and `sprint-prioritizer` (rank a 12-item backlog with a stated method).
5. Do **not** change scoring weights, judge sets, or evolution margins without writing the reason in
   STATUS.md first. The reviewer tunes those.

## Open questions for the local operator
- How long does a full `-Evolve` cycle take wall-clock on your machine with the retry waits?
- Does the scheduled task actually fire while the laptop is locked (not asleep)? Check `~/.evolvra/cycle.log`.
