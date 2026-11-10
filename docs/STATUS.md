# STATUS - round 14 (10 Nov 2026, local operator, model: Sonnet 5.5 throughout, no switch to Opus)

Reply to REVIEW.md "Requested now" (after STATUS 85aff4a). Verified = a command ran and I read its output.

## Items
| # | item | result |
|---|---|---|
| 1 | pull, tests, ruff | DONE - `f0903bb`; **74 passed** (25.6 s), ruff clean; plugin unchanged (0.3.7) |
| 2 | re-score the two 10 Nov missions, per judge before/after; rebuild judge input | DONE - 6 new calls (devops), 6 cached (frontend), 0 errors |
| 3 | one ux-researcher mission | DONE - usability-test kit + `score_sus.py`, PASS/PASS first try |
| cycle | `cycle.ps1`, no `-Evolve`, outside :15-:50 | DONE 11:47 AST, exit 0, `push: ok` (`7ab336d`) |
| 4 | this STATUS | DONE |

## Re-score of the QA tasks, per judge (corr / compl / qual / evid)
| task | judge | before | after |
|---|---|---|---|
| devops QA (`...045922...`) | gpt-oss | 0.0 / 0.0 / 0.4 / 0.3 "missing_or_incorrect_evidence" | 0.5 / 0.5 / 0.7 / 0.8 "missing_acceptance_criterion" |
| | Nemotron | error (unparseable output) | 1.0 / 1.0 / 0.95 / 0.95 |
| | Gemini | 1.0 / 1.0 / 0.9 / 1.0 | same |
| | **ensemble** | 0.5 / 0.5 / 0.65 / 0.65 | **0.75 / 0.75 / 0.9 / 0.875** (task fitness 0.8475) |
| frontend QA (`...051125...`) | gpt-oss | 0.5 / 0.5 / 0.8 / 0.6 "missing_one_open_test" | unchanged |
| | Nemotron, Gemini | 1.0 / 1.0 / 0.95-1.0 / 1.0 | unchanged |
| | **ensemble** | 0.75 / 0.75 / 0.875 / 0.8 | unchanged (task fitness 0.8362) |
Frontend: all 6 calls came from the cache because the judge input did not change (same prompt, same answer).
Devops: the mutant copy no longer leads, and Nemotron now parses. gpt-oss still scores 0.5-0.8; its new critique is "no verdict section marking each acceptance criterion" - true as far as files go: that QA agent gave its verdict only in chat, not in a file.

## Judge input rebuilt once (0 calls)
- **`QA-REPORT.md` does not exist in either 10 Nov QA folder.** Those QA agents returned their report as chat text and my handoff never asked for a file (the mission skill does not either). So the first file is the harness: `run-case.ps1` (devops), `qa_cdp.js` (frontend).
- **Mutants last: yes, devops.** `mutants/ (4 files)` is only in the "not shown" summary; no mutant script content is shown. The proofs `exitcodes.txt` is file 2. But 4 `selftest-m*.stdout.txt` (the mutants' output) are shown, `logs/big.log` (5.9 MB, excerpt) is file 3, and the QA's `expected-vs-actual.txt` is among the not-shown.
- **Frontend: the judge sees 1,153 of 6,356 chars of `03_cdp_transcript.txt` and 0 lines of the one-open checks** (A4-A6, A11, A12 are in the full file per the QA report; I did not open it myself). The budget goes to the driver script (5.8k chars) and the run-1 duplicates (`03a_*`, 4 files at ~1.15k each). This is the likely cause of gpt-oss's "missing_one_open_test".

## ux-researcher mission `20261110-083646-create-a-usability-test`
- Builder: moderator script (4 tasks, time limits 2/3/3/6 min), SEQ + 10 SUS items, findings template (severity 0-4), `score_sus.py` (stdlib; `--selftest` 22/22, I re-ran it: exit 0). PASS, ensemble 0.975 / 0.975 / 0.9 / 0.85.
- QA (asked to write a top-level `QA-REPORT.md` - it did, 7,972 bytes): hand-computed SUS for 8 participants matched exactly; straight-lining flagged; bad CSV cases exit 1/2 with no traceback. PASS, ensemble 0.9 / 1.0 / 0.9 / 0.875; gpt-oss alone "missing_evidence" (0.75).
- QA found: the builder's selftest catches 8 of 10 mutants (survivors: value 0 accepted; exit code 0 despite invalid rows); a non-ASCII participant id crashes the report on a cp1252 console; the one neutral prompt (after 2 min) can never fire in Task 1 (limit 2 min). None blocks; the kit has not been used with real participants.

## Numbers now (`evolvra fitness`)
ux-researcher 2 tasks 0.955 (min 0.95) - evidence-collector v2 15 tasks 0.933 (was 0.919, min 0.84) - devops-automator v2 3 tasks 0.974 (min 0.96) - frontend-developer 2 tasks 0.960.
Free tier today: OpenRouter 19/40 (resets 03:00 AST), Groq 20/800, Gemini 26/1000.

## Open questions for the reviewer
1. Should QA transcripts and results outrank the QA's own driver script and run-1 duplicates in the judge input, and should `*run1*`/`TEST_DRIVER_BUGS` files rank low? That would show the frontend one-open checks.
2. Add a line to the mission skill handoff asking QA agents to write a top-level `QA-REPORT.md` (verdict plus each criterion verified/not)? I did it by hand for this ux QA task and it worked; this needs a plugin version bump from you or me.
3. Next missions: a 4th devops v2 task, or sprint-prioritizer / content-creator (2-3 tasks each).
