# STATUS - round 12 (8 Nov 2026, local operator, model: Sonnet 5.5, no switch to Opus)

Reply to REVIEW.md "Requested now" (after STATUS 4857005). Verified = a command ran and I read its output.

## Items
| # | item | result |
|---|---|---|
| 1 | pull, tests, ruff, plugin 0.3.7 | DONE, but tests 72 passed / **1 FAILED** (reviewer expects 73) - see "What broke" |
| 2 | re-score reality-checker + devops, per judge before -> after, rebuild judge input | DONE, 9 calls, 0 errors |
| 3 | stop after item 2 and the cycle | stopped as the reviewer asked: no missions, no `-Evolve` |
| cycle | `.\scripts\cycle.ps1`, no `-Evolve` | DONE 13:45 AST, exit 0, `push: ok`, outside :15-:50 |
| 4 | this STATUS | DONE |

Setup (before this session, verified): `git pull --rebase --autostash` to `e993f51`, tree clean, 0 stashes.
Plugin updated 0.3.6 -> 0.3.7; cache SHA-256 of `agents\engineering-devops-automator.md` and `skills\mission\SKILL.md` equal the repo files. Ruff: all checks passed.

## What broke
**`tests/test_evals.py::test_thousands_of_fixtures_cannot_hide_the_report` (line 464) FAILS here**, same result alone and in a full run (deterministic on this PC). I changed no code or test.
- Failing assert: `"fx/ (" in text and "fx/file-0001.txt (" not in text.split("not shown")[0]` - it expects the fixtures to be only summarised.
- Actual: the report and `evidence/stress.txt` come first (the main point of 4dc5b1c works), then about 81 of the 1,200 fixture files are listed *with content*; the other ~1,119 are summarised as `fx/ (1119 files)`.
- My reading of `checks.py` `read_output` (lines ~154-165): low-priority files still fill whatever budget is left after the report and proofs. A 2 KB report leaves ~13 KB, which fits ~81 small fixtures. **Unverified**: why your run passed (73). Possible, not checked: a different fixture size, or the test relying on a larger report.
- The real missions are not affected by this (see re-scores): the report is first and proofs follow.

## Quota (`evolvra providers`)
Before: gemini 33/1000, groq 28/800, openrouter 31/40 (9 left, needed >=4). After: gemini 36, groq 31, openrouter **34/40 (6 left)**. Exactly 3 calls each; none cached (judge prompt changed).

## Re-score, per task and judge (correctness / evidence, failure class)
**Reality-checker, task 1** (`20261108-095120-reality-check-whether-the`)
| judge | before | after |
|---|---|---|
| gpt-oss-120b | 0.75 / 0.70 `missing_required_output` | 0.90 / 0.90 `none` |
| Nemotron | 0.75 / 0.90 `missing_deliverable` | 0.95 / 0.95 `none` |
| Gemini | 1.00 / 0.95 `none` | 1.00 / 0.95 `none` |
| **ensemble** | 0.75 / 0.90 `missing_required_output` | **0.925 / 0.925 `none`** |
| fitness | 0.843 | **0.9437** |

**Devops v2 task 1, builder** (devops-automator): all three judges 1.00 correctness, `none` before and after (gpt-oss evidence 0.90, Nemotron 1.00, Gemini 1.00 both times). Ensemble 1.00 / 0.95 -> 1.00 / 0.95. Fitness 0.9875 -> 0.98.

**Devops v2 task 2, QA** (evidence-collector)
| judge | before | after |
|---|---|---|
| gpt-oss-120b | 0.33 / 0.30 `missing_evidence` | **1.00 / 0.90 `none`** |
| Nemotron | 0.95 / 0.95 `none` | 1.00 / 1.00 `none` |
| Gemini | 1.00 / 0.95 `none` | 1.00 / 1.00 `none` |
| **ensemble** | 0.64 / 0.625 `missing_evidence` (contested by gpt-oss) | **1.00 / 0.95 `none`** (not contested) |
| fitness | 0.769 | **0.9875** |

**Plain answers:** (1) the reality-checker's false `missing_required_output` is **gone** - all three judges now say `none`. (2) gpt-oss **no longer marks the devops QA down** (0.33 -> 1.00). Caveat: one re-score each, free-tier judges vary a little between runs.
Agent fitness after the cycle: reality-checker 0.944 (1 task), evidence-collector v2 0.929 -> 0.947, devops-automator v2 0.972 -> 0.968.

## Judge input rebuilt, 0 API calls
Same `checks.read_output(...)` call and same `mentions` as `judge.build_prompt`, read-only DB. Script: scratch `judge_input.py` (not committed).
| task | prompt chars | files with content | `evidence/` files | report first? | omitted line |
|---|---|---|---|---|---|
| reality-checker 1 | 21,187 (read_output 17,076) | 10 | 9 | yes: `REALITY-CHECK.md` is #1 | 5 named, no "more"; folders `fx/ (395 files)`, `work/ (8 files)` |
| devops 1 builder | 20,649 (16,587) | 10 | 9 | n/a: `Test-Workflow.ps1` first (main deliverable) | 7 named (ci.yml, README.md, sample_project files); no folders |
| devops 2 QA | 20,286 (17,360) | 10 | 9 | yes: `QA-REPORT.md` is #1 | 25 named + "1 more"; folder `work/ (39 files)` |
Note: read_output alone is about 17k chars, a little above the 16k `total`, (the omitted line is appended after the budget check; not investigated further). The prompt wrapper adds about 3-4k.
The reality-checker output now shows `fx/ (395 files)`, not 6,458 (unverified why the count differs from the earlier 6,458; likely the folder-walk limit).

## Open questions for the reviewer
1. Why does `test_thousands_of_fixtures_cannot_hide_the_report` pass for you and fail here (81 fixtures shown)? Should low-priority files be capped when proofs exist, or is the test too strict?
2. Both fixes look good on real data; do you want gpt-oss's old 0.33 kept as a regression fixture?
3. Tomorrow per REVIEW: devops v2 mission #3 and frontend-developer or ux-researcher. OpenRouter will have 40 new calls; today 6 are left.

## Commits
- Cycle: `e555a5a` "cycle: refresh data (21 missions)" (pushed by cycle.ps1).
- STATUS: see git log (this file's commit is the newest on `main`).
- No code, test or plugin file changed this round.