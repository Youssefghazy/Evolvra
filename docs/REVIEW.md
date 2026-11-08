# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-08, after STATUS `4857005` (round 11)._

## Verdict
- **DevOps Automator v2: 2 of 2 real tasks, mean 0.972** (v1 0.881 over 4). One more task and we compare properly.
- **Backend QA fixed by the budget change** (fitness 0.645 → 0.98): gpt-oss agrees once it can see the proof.
- **Reality Checker's first task is the best QA work so far.** It found 4 reproduced gaps (junctions, duplicate zip
  entries, a report path that overwrote a source file, no same-folder guard) that the builder and QA both missed.
- Handling the usage-limit interruption by recording from disk instead of relaunching was correct.

## Fixed this round (tests 73, ruff clean, plugin 0.3.7)
1. **Scorer file cap before ranking** (your open question 1):
   - Every file is now ranked on metadata (path, size, mentions) before anything is cut. Only the files that make
     it into the prompt are read.
   - Folders of fixtures, copies, scratch, or **any unrecognised folder with more than 50 files** go last and are
     summarised as one line (`fx/ (6,444 files)`).
   - Tested with 1,200 fixture files: the report comes first.
2. **Many proof files** (your open question 2):
   - Proofs that the main report **cites by path** come first.
   - Each large proof gets at least ~800 characters; small proofs cost only their size.
   - Up to 25 omitted names, proofs first, plus folder counts.
   - Headers now count toward the 16k budget, so the prompt no longer grows to 18k.
   - A lone gpt-oss `missing_evidence` against two judges at the ceiling is already labelled `contested` and does
     not steer evolution. No new rule.
3. **Recording a standalone review** (your open question 3): your call was right. The mission skill now says it: a
   QA task with no builder to reopen is PASS when the review is complete, with the subject verdict first in the
   evidence text; FAIL only if the review itself is incomplete.
4. **Model** (your open question 5): Youssef's decision: **Sonnet 5.5 is the default** (CLAUDE.md rule 3 updated).
   Opus only for genuinely hard problems. Keep STATUS to about 80 lines to save usage.

## Requested now
1. `git pull`, tests: **expect 73**, ruff clean, plugin update to **0.3.7**, then a fresh session (Sonnet 5.5 is the default now; see CLAUDE.md rule 3).
2. Re-score with the new judge input, about 9 calls:
   - `--mission 20261108-095120-reality-check-whether-the --rescore` (your open question 4: yes);
   - `--mission 20261108-080705-devops-build-a-github --rescore`.
   Report per judge, before and after, and rebuild the judge input once for each (files shown, the omitted line).
3. Today's quota is mostly used and the PC is busy. **Stop after item 2 and the cycle** (`cycle.ps1`, no
   `-Evolve`, outside :15–:50). Tomorrow: one devops-automator v2 mission (the 3rd v2 task, then compare v2 vs v1),
   and one for frontend-developer or ux-researcher.
4. STATUS (about 80 lines) with `-- docs/STATUS.md`.
