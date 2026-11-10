# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-10, after STATUS `85aff4a` (round 13)._

## Verdict
- **DevOps Automator v2 is confirmed on real work:** 3 tasks, mean 0.973, min 0.96, against v1's 0.881 over 4
  (min 0.72). The README now shows it, with your caveat (different kinds of tasks, n=3).
- The sleep diagnosis (Kernel-Power 42 at 15:41, resume 07:43, no reboot, catch-up run at 07:49) was exactly right.
  Nothing to fix: the system works while the PC is awake.
- Generation 13 (backend-architect, −0.8) was a fair refusal.

## Fixed (tests 74, ruff clean; no plugin change)
1. **QA decoys** (your open question 1): `mutants/`, `sabotage/`, `broken/` and any file whose name contains
   "mutant" or "sabotage" now rank with scratch, never as the main file or as proof. The main file is now the
   named **top-level** file (the QA report), so a deliberately broken copy cannot be graded as the subject.
2. **`.log`, `.stdout`, `.stderr`, `.out`, `.err`, `.psm1`, `.bat`, `.tsv`** are read as text, not "binary".
3. **Safety:** files that look like secrets (`*.env`, `*.pem`, `*.key`, `id_rsa`, `credentials`) are never read
   into a judge prompt (which goes to external providers) and are never listed. `.env` had been on the text list.
4. Also new: `docs/DEMO-VIDEO.md`, the 60-second shot list for Youssef (built-in recording tools only).

## Requested now (short round)
1. `git pull`, tests: **expect 74**, ruff clean.
2. Re-score the two QA tasks with the fixed input (your open question 2: yes; about 6 calls):
   `uv run evolvra score --mission 20261110-045922-write-a-powershell-5 --rescore` and
   `uv run evolvra score --mission 20261110-051125-build-a-single-file --rescore`.
   Report the QA task per judge, before and after. Also rebuild the input once: is `QA-REPORT.md` first, and are
   the mutants at the end?
3. One mission for **ux-researcher** (1 task so far), your open question 3.
4. `.\scripts\cycle.ps1` (no `-Evolve`; the scheduled runs handle evolution while the PC is awake), outside
   :15–:50. Short STATUS with `-- docs/STATUS.md`.
