# Operator status (written by the local Claude Code session at the end of every working session)

## Session 2026-11-05 (11:30–12:10 AST, local operator, Opus 5.5, zero spend)

### REVIEW.md items (round 6)
| # | item | state |
|---|---|---|
| 1 | pull, plugin 0.3.2, tests | **done.** `48c767a`. `claude plugin marketplace update evolvra` + `claude plugin update evolvra@evolvra`: **0.3.1 → 0.3.2**. **62 passed**, ruff clean |
| 2 | full `score --rescore`, per-judge counts | **done, partly limited by budget.** 30 tasks, 90 judge calls, 19 cached, **14 errors**. Nemotron answered **18 of 30** before OpenRouter's 40/day cap. Numbers below |
| 3 | announcement rescore | **done.** The false "113 words" failure is **gone**: all three judges counted 101/104/104. **A new false failure replaced it** (gpt-oss rewrote a criterion). Details below |
| 4 | devops-automator mission + `cycle.ps1 -Evolve` | **mission done** (PASS first attempt, fitness 0.956). Cycle ran and pushed `69e51d1`. **Evolve skipped** (last generation 1.6 h earlier). First run that can evolve: the scheduled **6 Nov 04:17 AST** |
| 5 | validator folder | **done.** Youssef said yes in-session. Deleted only `…\20261105-073059-build-a-single-file\02-evidence-collector\scratch\validator` (844 files, 9.9 MB). `scratch\` still holds its 3 other files; `evidence\` untouched |

### Ran (in order)
- `git pull --rebase` → `48c767a`. Plugin refresh (above). `uv run pytest -q` **62 passed**; `uv run ruff check .` clean.
- No cycle was running at the start (`current.json` absent; the scheduled run had finished at 10:17). `evolvra providers`; `ping groq` and `ping openrouter` both returned `pong`.
- `evolvra score --mission 20261105-072406-write-a-product-announcement --rescore`: 08:36:58Z–08:38:01Z, 6 calls, 0 cached, 0 errors.
- `evolvra score --rescore`: 08:39:03Z–08:57:08Z (18 min), 30 tasks.
- Mission `20261105-084006-write-a-powershell-5` (recorder from the 0.3.2 install; single-quoted arguments).
- Deleted the validator folder (item 5).
- `.\scripts\cycle.ps1 -Evolve` 11:58:34–11:59:22 AST: ingest 1 mission / 111 traces, scored 2 tasks (6 calls, **2 errors** = OpenRouter cap), evolve skipped, export, push `69e51d1`. The pull before it also brought in `a7b0b30` (dashboard redesign, not mine).
- Per-judge numbers come from a read-only (`?mode=ro`) query of `scores`, filtered to rows written after 08:39:03Z.

### Item 2: Nemotron as a judge
| judge | verdicts / 30 | errors | mean of 4 rubrics | sd | min–max | correctness ≥ 0.95 | correctness = 1.0 | failure_class set |
|---|---|---|---|---|---|---|---|---|
| Groq gpt-oss-120b | **30** | 0 | 0.791 | 0.170 | 0.28–0.95 | 5 | 4 | 11 |
| OpenRouter Nemotron-3-ultra | **18** | 12 | 0.954 | 0.086 | 0.62–1.00 | 16 | 12 | 1 |
| Gemini 3.5 Flash-Lite | **28** | 2 | 0.980 | 0.030 | 0.85–1.00 | 27 | 27 | 1 |

- **Reliability:** all 18 Nemotron verdicts had valid scores. Of its 12 misses:
  - The 2 stored errors both read `daily cap reached for openrouter (40 requests)`.
  - The other 10 were not stored: when fewer judges answer than last time, `store_judge_results` keeps only the judges that answered, so error rows are dropped. Their cause is therefore not recorded. The cap is the likely one, since OpenRouter ended at 40/40, but an unparseable reply would look the same.
  - Gemini's 2 misses include one stored HTTP 503 ("high demand").
- **Nemotron costs about 2 requests per verdict.** OpenRouter used 34 requests for scoring today (40 minus 5 earlier pings and today's ping) and returned 18 Nemotron verdicts.
  - Since 08:30Z the cache holds 24 OpenRouter responses. **5 of them ended with `finish=length`.** The model spends its reasoning inside `MAX_TOKENS=900`, so the judge retries at 2400.
  - Empty truncated replies are not cached, so the real retry count is higher than 5.
  - At this rate, the 40/day cap covers about 20 Nemotron verdicts a day.
- **Spread:** Nemotron sits near the ceiling, though less so than Gemini.
  - In the 16 tasks where all three judges answered, the **most lenient on correctness** was Gemini 12 times, gpt-oss 3 and Nemotron 1. The **strictest was gpt-oss 16 of 16**.
  - Nemotron set a non-`none` failure class once in 18 answers.
  - So in practice the ensemble is two lenient seats plus one strict seat. gpt-oss's failure class decides the diagnosis almost every time.
- **The ensemble is now mixed.**
  - 19 tasks got a fresh ensemble: 16 from 3 judges (gpt-oss, Nemotron, Gemini) and 3 from 2 judges.
  - **11 tasks kept their older 3-judge ensemble that includes Qwen.** The guard behaved as designed: 2 fresh answers do not overwrite 3 older ones.
  - Finishing the switch needs about 22 more OpenRouter requests on a day with a fresh cap (open question 3).

### Item 3: announcement mission (content-creator task)
| | judges | correctness | completeness | evidence | quality | fitness | failure class |
|---|---|---|---|---|---|---|---|
| before (5 Nov 08:12Z) | gpt-oss, Qwen, Gemini | 0.75 | 0.90 | 0.40 | 0.85 | 0.8325 | `word_count_violation` (Qwen: "113 words") |
| after (5 Nov 08:37Z) | gpt-oss, Nemotron, Gemini | 0.70 | 0.75 | 0.90 | 0.90 | 0.8325 | `missing_feature_mentions` (gpt-oss) |

- **The measured facts work.** All three judges now state 101/104/104. Before, gpt-oss wrote "Agent claims counts within range"; now it writes "Word counts 101, 104, 104". The count failure is gone.
- **A new false failure took its place.** The criterion is `the text names exactly two product features`. gpt-oss rewrote it in its acceptance list as **"Each paragraph names exactly two product features"** and marked it unmet: "Paragraph 1 and 3 name no features; only paragraph 2 names two".
  - The text names exactly two features, Flow Sync and Recall Search, both in paragraph 2. I re-read the file to confirm.
  - Nemotron and Gemini both gave correctness 1.0. gpt-oss gave 0.4, so the median is 1.0 on correctness. The ensemble shows 0.70 only because the ceiling rule applies: two scores ≥ 0.95 → drop the most lenient → mean(0.4, 1.0).
  - The failure class comes from the strictest judge, so **`missing_feature_mentions` is now content-creator's top failure in `evolvra fitness`**. If content-creator becomes the evolution target, the diagnosis would be built on a misread criterion. Open question 1.
  - The QA task scored 0.98 (all three judges ≥ 0.9).

### Item 4: devops-automator mission
| task | agent | attempts | verdict | fitness |
|---|---|---|---|---|
| 1. `archive-logs.ps1`: zip `*.log` older than N days into `logs-YYYYMMDD.zip`, delete originals; `-WhatIf` and `-SelfTest` | devops-automator v1 | 1 | PASS | **0.956** (gpt-oss + Gemini; Nemotron hit the cap) |
| 2. Verify by running it, with counted evidence | evidence-collector v2 | 1 | PASS | 0.981 |

- **QA evidence (all re-checked from its files):**
  - parser 0 errors; `-SelfTest` 13 of 13 PASS, exit 0, no temp fixture left behind
  - `-WhatIf` on an 11-file fixture: 0 differences (name, SHA256 and LastWriteTime), 0 zips
  - real run: removed exactly the 4 expected old `.log` files; the other 7 kept with unchanged hashes; 4 zip entries, all hash-matched
  - search for download or install commands: 0 hits
  - script SHA256 `6FE6A739…837636` was the same before and after QA
- **Deviation the builder disclosed, which QA accepted:**
  - **What:** the zip is written with the in-box .NET `System.IO.Compression.ZipArchive` (from the GAC), not `Compress-Archive`.
  - **Why:** on this PC `Compress-Archive` (module 1.0.1) failed every time with "being used by another process": builder 3/3 plus 5/5 retries, QA 4/4. The module opens sources with no sharing.
  - **Cause:** the builder blames Apex One's on-access scan. **QA reproduced the failure but could not confirm that cause:** its own exclusive opens of the same files succeeded.
  - **Why QA accepted it:** criterion B5 names Invoke-WebRequest, Install-Module, external executables and downloads, and the script uses none of them.
- No download, no install and no Git Bash in either agent. Both handoffs carried the machine rules.
- **Fitness change:** devops-automator **0.805 (2 tasks) → 0.856 (3 tasks)**, still the weakest, so it is the next evolve target.

**Fitness now** (`evolvra fitness` after the cycle; "before" is the end of round 5):

| agent | ver | before (tasks) | now (tasks) |
|---|---|---|---|
| devops-automator | 1 | 0.805 (2) | **0.856 (3)**, still weakest |
| backend-architect | 1 | 0.863 (2) | 0.863 (2) |
| evidence-collector | 1 | 0.880 (8) | 0.872 (8) |
| growth-hacker | 1 | 0.903 (2) | 0.910 (2) |
| content-creator | 1 | 0.915 (3) | 0.923 (3) |
| evidence-collector | 2 | 0.924 (7) | **0.933 (8)** |
| frontend-developer | 1 | 0.975 (1) | 0.936 (1) |
| sprint-prioritizer | 1 | 0.956 (2) | 0.944 (2) |
| ux-researcher | 1 | 0.922 (1) | 0.953 (1) |
| rapid-prototyper | 1 | 0.923 (2) | 0.971 (2) |

v2 still leads v1 (0.933 vs 0.872, 8 tasks each). Every change in this table except devops-automator's new task comes from the judge swap.

**Evolve timing:**
- Generation 8 ran at 07:23Z, so the 12 h slot opens at 19:23Z (22:23 AST).
- The scheduled 22:17 AST run is 6 minutes early and will skip. The 04:17 AST run on 6 Nov should evolve devops-automator, the weakest current version.
- The replay guard is not needed for that run: generation 8's target was ux-researcher.
- OpenRouter resets at 00:00Z, so Nemotron will have its full 40 requests. A generation needs about 16 tournament verdicts, roughly 30 Nemotron requests at today's rate.

### What broke
1. **OpenRouter's daily cap (40) ran out during the full rescore.** 12 of 30 tasks have no Nemotron verdict, and the new mission's 2 tasks were scored by 2 judges. It was a hard stop, as designed: nothing was upgraded or paid.
2. **Judge rewrote a criterion** (item 3): a new false failure class on content-creator.
3. **`Compress-Archive` does not work on this PC** (file-in-use on every attempt). This matters for future bank tasks and missions that zip files.
4. Gemini HTTP 503 once (transient).
5. A small issue with my own tooling: printing judge evidence with `‑` (non-breaking hyphen) crashed Python on the cp1252 console. I fixed it with `PYTHONIOENCODING=utf-8` for the query. No engine change.

### Changes / commits
- **No code changes** (judges and weights are yours; tests still 62).
- Data commit from the cycle: `69e51d1`. This STATUS: see `git log -1 -- docs/STATUS.md`.
- Outside git: the plugin install was updated to 0.3.2 (restart needed for running sessions), and the validator folder was deleted (item 5).
- Usage today: Groq 47 requests / **188,684 tokens** (close to the ~200k rolling daily budget), Gemini 35 / 145,137 tokens, OpenRouter 40 / 40 requests. No paid calls.

### Open questions
1. **Criterion rewriting:** should the judge prompt require each acceptance entry to quote its criterion verbatim (or answer by index), and should `parse_verdict` reject or flag an entry whose text does not match? Today a rewritten criterion set the failure class, which feeds the evolution diagnosis. Separately: should a single judge's failure class win when the other two judges both gave correctness 1.0?
2. **Nemotron's budget:** it truncates at `MAX_TOKENS=900` often enough to average about 2 requests per verdict, so 40/day covers about 20 verdicts. Options:
   - an entry in `JUDGE_REASONING` (e.g. `"low"`) for Nemotron
   - a higher first-try budget for it
   - accepting 2-judge ensembles on busy days
3. **Finish the judge switch?** 11 tasks still carry Qwen-era ensembles. Should I run `score --rescore` again on a day with a fresh OpenRouter cap, at about 22 Nemotron requests plus the Groq tokens? The guard means only tasks where all 3 answer will be replaced.
4. **Leniency:** with Nemotron and Gemini both near the ceiling, the ceiling rule usually reduces to mean(gpt-oss, one lenient judge), and gpt-oss alone sets the diagnosis. Is that the balance you want?
5. **`Compress-Archive`:** should bank tasks and mission briefs that need zips say "in-box .NET `ZipArchive` allowed" up front, so builders don't spend retries rediscovering this?

**Still broken or unproven:** promotion on real-mission fitness is still unproven; the next real test is the 6 Nov 04:17 generation on devops-automator. The judge change is half applied (11 tasks on old ensembles). Judges can still misread a criterion's scope.
