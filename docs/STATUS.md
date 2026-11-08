# Operator status (written by the local Claude Code session at the end of every working session)

## Session 2026-11-08 (round 10): all 4 items handled

Local operator session, Sun 8 Nov ~10:55–11:40 AST. Opus 5.5, PowerShell only, no downloads or installs, no hand edits of records.
The PC is slow today (Trend Micro scanning after this morning's crash); nothing timed out.

### REVIEW.md items (round 10)
| # | item | state |
|---|---|---|
| 1 | pull, tests, ruff, plugin 0.3.5, fresh session | **done.** `git pull --rebase --autostash` to `0f94695`. My uncommitted 0.3.5 bump was byte-identical to yours (blobs `5e0534b`, `13092b1`), so the tree is clean and there are 0 stashes. **71 passed** (21.3 s), ruff clean. Plugin updated 0.3.4 → **0.3.5**. A new session was started for the rest. Details below |
| 2 | re-score the backend mission | **done.** 6 calls (3 cached, 0 errors). The QA "missing evidence" is **smaller but not gone**: Nemotron cleared it, gpt-oss still raises it. Before/after below |
| 3 | one devops-automator mission on v2 | **done.** `20261108-080705-devops-build-a-github`: GitHub Actions CI workflow + built-ins-only PowerShell checker. Builder PASS, QA PASS, 1 attempt each |
| 4 | `cycle.ps1` (no `-Evolve`) + STATUS | **done.** 11:28:44–11:29:53, exit 0, `push: ok` (`b1663ce`). This STATUS is committed with `-- docs/STATUS.md` |

### Item 1: devops v2 reaches missions (checked in this new session)
- `claude plugin list`: `evolvra@evolvra` Version **0.3.5**, enabled.
- `installed_plugins.json`: installPath `...\plugins\cache\evolvra\evolvra\0.3.5`, gitCommitSha `0f94695...`.
- The mission skill loaded from `C:\Users\Training1\.claude\plugins\cache\evolvra\evolvra\0.3.5\skills\mission`, and the recorder path it gave was the 0.3.5 one.
- The cached `engineering-devops-automator.md` SHA-256 is `02BE3EBC...E0A3`, the same as the repo's `plugin/agents/` file (v2). The 0.3.4 cache copy (v1) is `962F1E25...0AB4`. The 0.3.5 `MANIFEST.json` has devops-automator `"version": 2`, parent 1.

### Item 2: re-score of `20261108-064726-build-a-small-stdlib` (correctness / evidence, failure class)
"Before" = the latest rows before the run (judges 07:42–07:43Z, ensemble reaggregated 07:50Z), read with `?mode=ro`, `rubric:error` rows left out. "After" = 08:05–08:06Z.

| task | judge | before | after |
|---|---|---|---|
| #1 backend-architect | gpt-oss | 1.00 / 0.80 none | 1.00 / 0.80 none (cached) |
| | Nemotron | 0.95 / 0.80 none | 0.95 / 0.80 none (cached) |
| | Gemini | 1.00 / 0.95 none | 1.00 / 0.95 none (cached) |
| | **ensemble** | 0.975 / 0.80 none | 0.975 / 0.80 none; fitness **0.9525** (unchanged) |
| #2 evidence-collector | gpt-oss | 0.00 / 0.20 `missing_evidence` | **0.00 / 0.10** `missing_verifiable_evidence` ("lacks any captured command output verifying the claimed tests were actually executed") |
| | Nemotron | 0.50 / 0.20 `missing_evidence` | **1.00 / 1.00 none** |
| | Gemini | 1.00 / 0.95 none | 1.00 / 1.00 none |
| | **ensemble** | 0.50 / 0.20 `missing_evidence` | **0.50 / 0.55** `missing_verifiable_evidence`; fitness 0.625 → **0.645** |

Only task #2's prompt changed, so its 3 calls were new and task #1's 3 were cached.

**Answer: "missing evidence" is not fully gone.** Nemotron's false claim ("all evidence files are empty") is gone. gpt-oss still says no captured output is visible, and with the trimmed-low mean one judge is enough to hold the ensemble at 0.50.

**What the judge now sees** (rebuilt offline with the same `checks.read_output(...)` call as `judge.build_prompt`; 0 API calls; 14,705 chars):
1. `independent_check.py` (6,206 chars): the main deliverable. The `work/notes_api.py` copy is no longer first, so that part of the fix works.
2. `evidence/b1-unittest-builder-dir.txt`, `evidence/b1-unittest-copy-run1.txt`, `evidence/b1-unittest-copy-run2.txt` (2,675 chars each): **proof files now come early.**
3. `[7 more file(s) omitted to fit the prompt]`. This includes `independent-process-check.txt`, `b3-import-scan.txt`, `00-hashes-before.txt` and `99-final-state.txt`.
4. **The 0-byte captures are still listed:** `evidence/b1-unittest-copy-run1.txt.stdout`, `...run2.txt.stdout` and `independent-process-check.txt.stderr`, each as "(binary, 0 bytes)".
   - Cause: in `checks.py:84-86` a file whose suffix is not in `TEXT_SUFFIXES` goes to `binaries` before the empty-file check at line 91. So "empty files are not listed" only applies to text suffixes.
   - Fix idea (not made): `if path.stat().st_size == 0: continue` before the suffix test.

gpt-oss had 3 unittest captures in front of it and still said "no captured output". So at least part of this is the judge, not the file order. See open question 2.

### Item 3: devops-automator v2 mission `20261108-080705-devops-build-a-github` (micro, NEXUS)
- **#1 devops-automator (v2), 1 attempt, PASS.**
  - `ci.yml`, plus a byte-identical `.github/workflows/ci.yml`: push to main and pull_request; job `test` on `ubuntu-latest`; `permissions: contents: read`; matrix `"3.11"` to `"3.14"`; `actions/checkout@v5` and `actions/setup-python@v6`; `python -m unittest discover -s tests -t . -v`.
  - `Test-Workflow.ps1`: built-ins only, with its own YAML-subset parser and 17 checks.
    - `-Path ci.yml` gives 17/17 PASS, exit 0.
    - `-SelfTest`: 9 good workflows are accepted, and 28 broken ones are each rejected **by the check they target**. Exit 0. A sabotaged copy exits 1.
  - The sample project `mathkit` has 15 tests, all OK, exit 0.
  - The builder said itself that the workflow was not run on GitHub, and that the @v5/@v6 tags and Python 3.14 on ubuntu-latest were not checked online.
- **#2 evidence-collector (v2), 1 attempt, PASS.**
  - It re-ran every builder criterion, with 12 non-empty evidence files.
  - It tried 23 new workflows: 16 broken and 7 valid but unusual.
  - The builder folder's hashes were the same before and after.
  - It found 4 checker gaps, none of them blocking:
    - C17 passes when unittest never runs (a `#` comment line, `if: false`, or `echo python -m unittest`).
    - Matching is case-insensitive where it should not be (`-contains`/`-notmatch` accept `Push` and `@V5`).
    - Event names and job/step keys are not validated (a dedented `branches:` and the typos `timeout-minute` and `whit:` are accepted).
    - Quoted values inside one-line `{ }` maps are misread. This fails safe.
- **Machine notes line** (Compress-Archive fails, so use in-box .NET ZipArchive; PowerShell not Git Bash) was in both handoffs. Neither agent used Git Bash or downloaded anything.
- Nothing was registered, pushed or installed. All files stay in `~\.evolvra\missions\20261108-080705-devops-build-a-github\`.

**Score lines from the 11:28 cycle (ensemble; correctness / completeness / evidence / quality):**

| task | ensemble | per judge (correctness / evidence) |
|---|---|---|
| #1 devops-automator v2 | 1.00 / 1.00 / 0.88 / 0.905, none | gpt-oss 1.00 / 0.81; Nemotron 1.00 / 1.00; Gemini 1.00 / 0.95 |
| #2 evidence-collector v2 | 0.665 / 0.70 / 0.625 / 0.90, `missing_evidence` | gpt-oss **0.33 / 0.30** `missing_evidence` ("lacks visible evidence files"); Nemotron 1.00 / 0.95; Gemini 1.00 / 0.95 |

- The same pattern again: gpt-oss alone marks the QA task down for evidence it was not shown.
- The rebuilt judge input for this QA task (0 calls, 13,597 chars) is: `QA-REPORT.md` (11,419 chars), then `evidence/07-new-cases-summary.txt` (4,743 chars), then `[73 more file(s) omitted to fit the prompt]`.
  - The main report uses `PRIMARY_CHARS` = 10,000 of the 16,000 total, so only one proof file fits.
  - Also, the cutoff test at `checks.py:116` stops at the first file that does not fit whole, without sending a shorter excerpt of it.
  - So a QA agent that writes a thorough report is shown with almost none of its proof.

**DevOps Automator v2 on real work so far: 1 task** (this mission's #1), fitness **0.974**. v1: 4 tasks, mean 0.881 (`evolvra fitness`).
The v2 vs v1 comparison **waits for 3 or more v2 tasks**, as agreed. One task is not a trend.

### Ran (in order, AST)
1. (Before this session) `git pull --rebase --autostash` to `0f94695`; `uv run pytest -q`: **71 passed in 21.33s**; `uv run ruff check .`: All checks passed!; `claude plugin marketplace update evolvra` and `claude plugin update evolvra@evolvra`: "updated from 0.3.4 to 0.3.5". Cached persona hash checked (see item 1).
2. ~11:00 New session: `claude plugin list`, read `installed_plugins.json`, compared the persona hashes.
3. 11:04 Read-only (`?mode=ro`) snapshot of the `scores`/`tasks`/`missions` rows for the backend mission. Read the `cycle.log` tail as bytes: the last run, 10:50:39, has an end line.
4. 11:05:16–11:06:13 `uv run evolvra score --mission 20261108-064726-build-a-small-stdlib --rescore` gave `judge calls=6 cached=3 errors=0`; #1 fitness 0.9525, #2 fitness 0.645. Exit 0.
5. 11:06 Rebuilt the judge `output` block offline (`checks.read_output`), 0 API calls.
6. 11:07–11:28 Mission `20261108-080705-devops-build-a-github`, run with the recorder: start, task add ×2, task start/done ×2, finish `done`.
   - The builder subagent took ~12.6 min and the QA subagent ~7.2 min.
7. 11:28:44 `.\scripts\cycle.ps1` (no `-Evolve`). This is outside the :15–:50 window, and the previous cycle had ended.
   - `ingest: missions added=1 updated=18 invalid=0 | traces added=90 skipped=1024`
   - `score: tasks scored=2 skipped=0 | judge calls=6 cached=0 errors=0`
   - `reaggregate: 38/38 ensembles, 0 calls`
   - `export: agents.json=10, missions.json=19, evolutions.json=12, summary.json=1`
   - `push: ok`, then `[2026-11-08 11:29:53] cycle end (exit 0)`; `$LASTEXITCODE` = 0. Commit `b1663ce`.
8. 11:30 Rebuilt the QA task's judge input offline (0 calls); `evolvra missions`, `evolvra fitness`; read `provider_usage` read-only.

### Numbers
- Tests 71; ruff clean (before this session).
- Missions 19. Today: 3 missions, 6 tasks, all PASS.
- Provider use on 8 Nov (UTC day): gemini **27**/1000, groq **22**/800, openrouter **24/40**.
- `evolvra fitness` (agent, version, tasks, mean):
  - devops-automator v1: 4 tasks, 0.881
  - devops-automator **v2: 1 task, 0.974**
  - evidence-collector v1: 8 tasks, 0.872
  - evidence-collector v2: 11 tasks, 0.895
- The cycle's push exit code was 0 and cycle.log ends with `cycle end (exit 0)`. That was the first run with the new exit code, so the new end line shape is confirmed.

### Verified vs not verified
- **Verified:**
  - Plugin 0.3.5 is enabled, and the mission skill and recorder loaded from the 0.3.5 cache.
  - The cached persona is v2 (hash match).
  - The before/after score rows (DB, read-only).
  - The judge file order for both QA tasks, rebuilt locally.
  - The checker gap in `checks.py:84-86` (code read).
  - That the mission's output files exist. I listed the builder folder and read the self-test and unittest tails myself (`28/28`, `OK`, `EXIT CODE: 0`).
  - Cycle exit code 0, and `push: ok`.
- **Not verified:**
  - The CI workflow was **not run on GitHub**.
  - The `@v5`/`@v6` tags and Python 3.14 on `ubuntu-latest` were not checked online.
  - The tests ran only on Python 3.13.15.
  - The QA agent's 23 new-case results: I read its report, but did not re-run the cases myself.
  - Why gpt-oss says "no captured output" when 3 captures are in its prompt (I did not read its raw reply).

### What broke
1. The QA "missing evidence" is still there for the backend mission (gpt-oss), and it appeared again on today's devops QA task (gpt-oss 0.33 / 0.30).
2. 0-byte files with non-text suffixes are still listed as "(binary, 0 bytes)" (`checks.py:84-86`).
3. A long QA report pushes nearly all proof out of the judge prompt: 73 of 75 files were omitted for the devops QA task (`PRIMARY_CHARS` 10,000 of 16,000; `checks.py:116` stops instead of sending a shorter excerpt).
- Nothing failed in the run itself: 0 judge errors, 0 retries, cycle exit 0.

### Changes / commits
- No code, test, record, trace or DB hand edits. No changes to `core/` or `plugin/`.
- `b1663ce` cycle: refresh data (19 missions), with the re-score and the new mission exported.
- This STATUS: committed with `-- docs/STATUS.md`. See `git log -1 -- docs/STATUS.md`.

### Open questions
1. **0-byte files:** skip any file with `st_size == 0` before the suffix test in `read_output`?
2. **QA proof budget:** for QA tasks, should the main report be capped lower (for example 5,000 chars) so several `evidence/` files fit? Should the cutoff send a shorter excerpt instead of stopping? gpt-oss is the lone dissenter on 2 of the last 3 QA tasks (on the third, the 8 Nov PowerShell QA, Nemotron was). If it keeps flagging evidence that is visible, should its QA evidence verdict be marked "contested", as was done for `missing_implementation`?
3. **Checker gaps found by QA (C17 / case / keys):** worth a bank task for devops-automator ("a CI checker must prove the test step actually runs"), since the next evolution reads real failures? It is not a failure today (the builder passed), so I left it.
