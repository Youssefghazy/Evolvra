# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-08 ~07:40Z, after STATUS `9c2719f` (round 8)._

## Verdict
Excellent round. The two results that matter:
- **The hook is shell-free.** In 529 process polls over 2 minutes, no bash.exe or sh.exe appeared, and traces still
  grew one line per tool call. The 5 Nov signature (`bash.exe <- claude.exe`) is gone. Tell the network admin when
  convenient; only their console can confirm the alerts stopped.
- **Nemotron is 1:1** (7 Nov: 12 requests, 12 verdicts), and gpt-oss now answers by criterion id.

Finding "weekend cycles never pulled" in cycle.log was the most useful catch of the round.

## Fixed this round (tests 70, ruff clean; no plugin change)
1. **Your open question 1 was a scorer bug, not harsh judges.** `read_output` capped the folder at 20 files
   (alphabetical), fed the largest file first, and labelled files by bare name. A QA folder with a large harness
   script, many scratch files and small `evidence/*.txt` proofs therefore sent the harness and lost the proof.
   - Files the agent's evidence statement or the criteria mention now go first (matched by path or name, `\` or `/`).
   - `scratch/`, `fixtures/` and `tmp/` go last.
   - Every file is labelled with its path inside the folder.
   - The cut-middle marker now says the omitted text exists and must not be reported as missing; if a criterion
     depends on it, the judge must say it could not be verified from the excerpt. This targets gpt-oss's
     "missing_implementation" on the 20 KB devops script.
2. **Weekend cycles ran old code** because the stray STATUS edit blocked `git pull --rebase`. `cycle.ps1` and the
   cycle's retry now use `--autostash`, so a local edit can no longer stop the pull.

## Decisions on your open questions
1. Fixed above. **Re-score the two new missions** so their 4 tasks are judged on what the agents actually produced
   (item 2).
2. **A missing criterion id** (gpt-oss skipped C4): no change. The rubric numbers are the judge's own; a skipped id
   is treated as not graded, not as failed.
3. **One extra OpenRouter request:** expected. That is the JSON-repair retry or a truncation retry. 1:1 on a full
   day is the number that matters.
4. **`stash@{0}`:** it is superseded (its content is committed in `523bcc5`). Drop it if Youssef agrees in-session.
5. **Generation 12:** the 10:17 run should retry devops-automator with all 3 rewrites (Gemini writes any that are too
   large for Groq). Report it.

## Requested now (short round)
1. `git pull` (expect `cycle: refresh data` from the 10:17 run plus this commit). Tests: **expect 70**; ruff clean.
   No plugin update is needed.
2. Re-score today's missions with the fixed scorer (about 12 judge calls):
   - `uv run evolvra score --mission 20261108-063451-write-a-powershell-5 --rescore`
   - `uv run evolvra score --mission 20261108-064726-build-a-small-stdlib --rescore`
   Report per task, before and after: each judge's correctness and evidence scores, and the failure class. Did the
   "missing evidence" and "missing_implementation" calls go away?
3. Report generation 12 from cycle.log, the evolutions folder and the DB:
   - target, delta, outcome;
   - each candidate's author (Groq or the Gemini fallback);
   - verdicts per judge.
4. `.\scripts\cycle.ps1` (no `-Evolve`) to export the re-scores. Mind the scheduled run: not between :15 and :50
   past 04/10/16/22, or while cycle.log shows a start without an end.
5. With Youssef's OK, `git stash drop stash@{0}`. STATUS as usual (commit with `-- docs/STATUS.md`).
