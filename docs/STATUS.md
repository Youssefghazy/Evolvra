# STATUS - round 15 (10 Nov 2026, local operator, model: Sonnet 5.5 throughout, no switch to Opus)

Reply to REVIEW.md "Requested now" (after STATUS b475949). Verified = a command ran and I read its output.

## Items
| # | item | result |
|---|---|---|
| 0 | demo video | DONE - `Downloads\evolvra.mp4` moved to `media/evolvra-demo.mp4` (34.4 MB, under 100 MB), committed alone with a pathspec, pushed `04b3305`. Not re-encoded, nothing installed |
| 1 | pull, tests, ruff, plugin 0.3.8, fresh session | DONE - pulled `80b27bd`; **75 passed** (28.1 s), ruff clean. `claude plugin marketplace update` + `plugin update`: 0.3.7 -> 0.3.8; cache SHA-256 of `skills\mission\SKILL.md`, `agents\engineering-devops-automator.md`, `plugin.json` equal the repo. The mission ran in a fresh session ("evolvra-round15", Sonnet 5.5), which reported plugin 0.3.8 |
| 2 | re-score frontend mission, QA per judge | DONE, but **the QA task got worse** - see below |
| 3 | sprint-prioritizer mission, does QA write `QA-REPORT.md` alone? | DONE - **yes**, PASS/PASS first try |
| cycle | `cycle.ps1`, no `-Evolve`, outside :15-:50 | DONE 12:33 AST, exit 0, `push: ok` (`16088e1`) |
| 4 | this STATUS | DONE |

## Frontend QA re-score (new judge input), per judge (corr / compl / qual / evid)
| judge | before (round 14) | after |
|---|---|---|
| gpt-oss | 0.5 / 0.5 / 0.8 / 0.6 "missing_one_open_test" | **0.0 / 0.0 / 0.2 / 0.3** same class |
| Nemotron | 1.0 / 1.0 / 0.95 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 |
| Gemini | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 |
| **ensemble** | 0.75 / 0.75 / 0.875 / 0.8 (task 0.836) | **0.5 / 0.5 / 0.6 / 0.65 (task 0.655)** |
6 judge calls, 3 cached, 0 errors. Two of three judges say 1.0; gpt-oss alone moved down by 0.5 on the same class.
Why the fix does not help this folder (I rebuilt the input again, 0 calls): the folder has **no report file** (the QA ran before 0.3.8), so the ranking is the same as before: `qa_cdp.js` first (5.8k chars), then results.json and the transcript. The transcript now gets 1,417 of 6,356 chars (was 1,153); the one-open lines (A4-A6, A11, A12) are still not in what the judge sees (0 lines). So gpt-oss still cannot find the evidence, and its verdict is the same, harsher. The new ranking only helps folders that contain a report.

## Sprint-prioritizer mission `20261110-092831-plan-a-6-week` (plugin 0.3.8)
- Builder: `sprint-plan.md` + `.csv`, RICE for 9 features, chosen set 59 of 60 usable days, dependency respected (Shared notebooks not chosen; Sync conflict fixes chosen). PASS, ensemble 1.0 / 1.0 / 0.95 / 1.0 (all three judges 0.9-1.0).
- QA wrote **`QA-REPORT.md` on its own** (1,448 bytes, top level of its folder, line 1 `VERDICT: PASS (all 5 builder criteria verified; 0 mismatches)`, one line per criterion with the proving file). I checked the file myself; my handoff did not ask for it, only the 0.3.8 skill template did. It also brute-forced all 512 subsets and found the builder's set optimal. PASS, ensemble 1.0 / 1.0 / 0.925 / 0.95.
- Minor QA wording notes only ("close" in risk 3 is generous).

## Numbers now (`evolvra fitness`)
sprint-prioritizer 3 tasks 0.964 (was 0.950, 2) - evidence-collector v2 16 tasks 0.924 (min 0.66 = the frontend QA task above) - devops v2 3 tasks 0.974 - ux-researcher 2 tasks 0.955.
Free tier today: OpenRouter 22/40 (resets 03:00 AST), Groq 23/800, Gemini 29/1000.

## Open questions for the reviewer
1. Old QA folders without a report (like the frontend one) are still cut: should a big driver script (`qa_cdp.js`, 15 KB) rank below transcripts/results, or get a smaller share of the budget, so a 6 KB transcript is shown in full?
2. Is a re-score allowed to lower an old task's score because the judge input changed but gpt-oss varied? Keep it, or fix by re-running the frontend QA with 0.3.8 so it writes a report?
3. Next missions: content-creator (3 tasks), rapid-prototyper (2), or a 4th devops v2 task.
