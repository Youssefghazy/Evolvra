# Operator status (written by the local Claude Code session at the end of every working session)

## Session 2026-11-03 (12:57–15:15 AST, local operator, Opus 5.5, zero spend)

### REVIEW.md items (round 2)
| # | item | state |
|---|---|---|
| 1 | pull + plugin 0.3.0, ask Youssef to restart | **done** via CLI. Later refreshed to **0.3.1** (see below). **Restart still pending** |
| 2 | re-score everything, before/after fitness | **done**, three passes, because the re-score exposed 3 engine bugs (fixed below) |
| 3 | bank shows "(materials embedded)" | **done**: 6 mission-derived tasks, all embedded, plus 3 seeds |
| 4 | one `-Evolve` cycle | **done**, and it produced the **first promotion**: evidence-collector v1 → v2 |
| 5 | annotate mission 3 with `note` | **done**: 2 notes (task 1, task 2); attempts untouched |
| 6 | rapid-prototyper + ux-researcher missions | **done**: both PASS on the first attempt, QA-verified. No natural QA failure, so `reopened` was not exercised |
| 7 | don't touch weights / judges / margins / actor | respected. My fixes are engine bugs (parsing, caching, file collection, attribution, logging). Each reason is below |

### Ran (all commands, in order)
- `git pull --rebase` → `cc05264`.
- Tests: `uv run pytest -q` 49 passed at the start, **54 passed** at the end. `uv run ruff check .` is clean throughout.
- `claude plugin marketplace update evolvra` + `claude plugin update evolvra@evolvra`: 0.2.0 → 0.3.0, later 0.3.0 → 0.3.1. The cache files `cmp`-identical to the repo: mission.py, log_event.py, SKILL.md, testing-evidence-collector.md.
- `uv run evolvra score --rescore` ×3 (12 tasks), plus `--mission 20261103-075105-write-a-github-actions --rescore` once.
- `uv run evolvra bank evidence-collector`.
- `python plugin/scripts/mission.py note 20261103-080434-propose-three-zero-budget --task 1|2 --text …`.
- `.\scripts\cycle.ps1 -Evolve`: 13:40:24 → 14:37:35, **3434 s (57 min)**.
- Missions `20261103-104040-build-a-single-file` (rapid-prototyper) and `20261103-104658-write-a-user-interview` (ux-researcher).
- `.\scripts\cycle.ps1` (data only): 14:42:19 → 15:04:05, **1308 s (22 min)**, ingesting and scoring the 2 new missions.

### REVIEW 2: fitness before/after the new ensemble
| agent | old ensemble (median, Gemma) | new ensemble, first pass | new ensemble, after my 3 fixes |
|---|---|---|---|
| evidence-collector (6 tasks) | 0.751 | 0.661 | **0.822** |
| backend-architect | 0.777 | 0.895 | **0.848** |
| growth-hacker | 0.988 | 0.575 | **0.882** |
| sprint-prioritizer | 0.988 | 0.970 | **0.970** |
| devops-automator | 0.990 | 0.343 | **0.830** |
| content-creator | 0.993 | 0.985 | **0.968** |
| frontend-developer | 0.995 | 0.975 | **0.975** |

- **Scores came off the 1.0 ceiling.** No agent is at 0.99 any more; the range is now 0.83–0.98.
- **The first pass was mostly artefacts, not judgement:**
  - devops 0.34 was my own `20814d5` bug (below).
  - growth-hacker 0.575 and part of evidence-collector came from truncated judge JSON being read as all zeros (below).
- **Qwen 429s (REVIEW open question).** Groq enforces three different caps on Qwen; details under "Judge-set facts".

### Bugs found and fixed (commits on `main`, each test-first)
1. **`852c6f5` Scorer: my `20814d5` hid `.github/`.** The fix skipped *every* dot-directory, so the judges never saw `.github/workflows/ci.yml` and devops-automator scored **0.34 "missing_deliverable"**.
   - Now only known tool dirs are pruned (`.venv`, `.git`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.tox`, `.nox`, `.cache`, `.ipynb_checkpoints`), plus any directory holding `pyvenv.cfg` (QA had made a venv called `cleanvenv`).
   - I checked every task dir: only the 2 GitHub-Actions tasks changed. After re-scoring, devops is **0.83**.
2. **`5152a81` Judges: Qwen ran out of budget.** Qwen 3.8 on Groq spent all 900 output tokens on hidden reasoning (`finish_reason=length`, empty content) in 10 of 14 calls.
   - The client also **cached those empty replies**, so every re-score replayed the failure.
   - Fix: a truncated reply with no verdict is retried once with `max_tokens=2400`, and empty truncated replies are no longer cached. Judge set, prompt and weights are unchanged.
3. **`1802d2e` Judges: a truncated reply was read as all-zero scores.** A reply cut off mid-JSON still contains a complete inner object (one acceptance item). `parse_judge_json` returned it, every metric clamped to 0.0, and the trimmed-low mean averaged the zeros in.
   - Example: growth-hacker got 0.41, where the two judges that answered gave 0.82–0.90.
   - Found in Flash-Lite and Qwen replies.
   - Fix: `parse_verdict` requires all 4 rubric keys; otherwise the reply goes through the retries above.
4. **`919d1b3` Ingest: wrong version credited.** Ingest credited a task to the version current *at ingest time*.
   - My two missions ran under evidence-collector v1 after the cycle's ingest, and the cycle then promoted v2. The next ingest would have credited their QA tasks to v2.
   - Fix: a task maps to the latest version created at or before its first attempt's start.
   - **Verified:** both new QA tasks are recorded as v1.
5. **`7c25923` Plugin 0.3.1.** The promotion rewrote `plugin/agents/` without a version bump, so the installed plugin would keep running v1. You have since made the engine bump the version itself (`1d0c768`, thanks). The installed copy is now 0.3.1 with v2 (`cmp`-identical).
6. **`02089da` + `33e2148` cycle.ps1 logging was mixed UTF-16/UTF-8.**
   - `Tee-Object -Append` writes UTF-16 under Windows PowerShell 5.1 (which the scheduled task uses) and UTF-8 under pwsh 7. So `cycle.log` is mixed, and `grep` missed every scheduled run. That is why last session I could not find them.
   - My first fix (`Add-Content -Encoding UTF8`) failed with "Stream was not readable" on the real log, which starts with a UTF-16 BOM. **The 14:42 data cycle therefore wrote nothing to `cycle.log`.** Its console output is preserved, and the numbers here come from it.
   - Final fix: `[IO.File]::AppendAllText` with UTF-8. Tested under `powershell.exe -File` on a copy of the real log, stdout and stderr lines both appended.
   - The old UTF-16 lines are left as they are, because I did not rewrite the log.

### REVIEW 4: evolution generation `20261103-104027-evidence-collector`
```
ingest: missions added=0 updated=6 | traces added=73 skipped=218
score: nothing new
evolve: PROMOTED evidence-collector v1 -> v2 (candidate 3, paired delta +0.1662 on 4 shared task(s), fitness 0.6288 -> 0.795)
```
| persona | target | proxy fitness | paired delta | coverage |
|---|---|---|---|---|
| parent v1 | – | 0.6288 | – | 4/4 |
| candidate 1 | unverifiable_evidence | 0.744 | +0.1152 | 4/4 |
| candidate 2 | invalid_workflow_content | 0.7188 | +0.090 | 4/4 |
| candidate 3 **winner** | unverifiable_claims | 0.795 | +0.1662 | 4/4 |

- **The actor did not saturate.** The parent scored 0.61 / 0.92 / 0.46 / 0.525 on the four bank tasks; none were at 1.0.
  - Parent per task: BACKLOG 0.61 "fabricated evidence for the calculations"; star-rating 0.92; EXPERIMENTS 0.46; workflow 0.525 "lacks actual YAML parsing and actionlint output".
- **The bank used was the 4 newest mission-derived tasks only.** The frontend and sprint QA tasks, GitHub Actions and EXPERIMENTS were used; the seeds were not.
- **What v2 changes** (19 lines in `plugin/agents/testing-evidence-collector.md`):
  - a new "STEP 2: Capture All Command Outputs" (save every command's raw output under `evidence/`);
  - an automatic-fail rule for claims without a referenced raw file;
  - a "Raw Evidence Files" section in the report template.
  - It is sensible, and it matches what the best real QA runs already do.
- **Provider requests in this cycle.** Counted as new `llm_cache` rows, so failed calls are not counted and this is a floor: Gemini Flash-Lite 32, gpt-oss-120b 14, **Qwen 2** = 48. So the arena was judged almost entirely by 2 judges. With fewer than 3 answers, the trimmed-low mean is a plain mean.
- **Wall clock:** 57 min, versus 15 min of evolution last session. I assume most of it was rate-limit waits on Groq (Qwen OTPM/TPD), but this is not verified per step.

**Caveats on this promotion (your call, I did not change anything):**
- (a) n=4 tasks, one actor sample each, ~2 judges.
- (b) 2 of the 4 bank tasks are partly unwinnable for the arena actor:
  - "Workflow": its criteria require *running* YAML/actionlint. Flash-Lite cannot execute, so candidates are rewarded for "honest hypothetical evidence" (cand 3 got 0.74, "Evidence is hypothetical rather than executed").
  - "EXPERIMENTS": the embedded materials are truncated (next point).
- The delta is +0.166 against a +0.03 margin, so the result is probably robust to noise. But it rewards "save raw outputs" mostly through the 2 tasks the actor can actually do.

### Judge input is truncated, and this is now the biggest scoring distortion
- **Scorer:** `checks.read_output` shows judges only 4,000 characters per file and 12,000 in total.
- **ux-researcher → 0.605.** The guide is 14.7 KB, and its "Main questions" section starts at line 117, past the cut. Two judges said "deliverables … missing or not visible" / "output file was truncated mid-text". QA (which read the whole file) verified every criterion.
- **growth-hacker (EXPERIMENTS.md, 26 KB).** Same "truncated in preview" critiques.
- **Bank materials:** `bank.materials_for` uses the same reader. For EXPERIMENTS, the stale `EXPERIMENTS.attempt1.md` (17 KB, saved by mission 3's orchestrator) **sorts first and uses half the budget**. The arena actor then sees parts of attempt 1 and parts of the final version.
- Not changed: it is a token-budget and Groq-TPM trade-off, so it's yours. Options:
  - (a) raise `per_file` for the single main deliverable;
  - (b) skip `*.attempt*` / backup files;
  - (c) give judges a head+tail or section-aware excerpt;
  - (d) exclude long-document tasks from the bank.

### Judge-set facts you need (REVIEW open question: Qwen and the 8k TPM)
Groq caps on Qwen 3.8, seen in the error bodies:
- **Output tokens per minute: 1,000.** A request with max_tokens 2400 is refused outright ("Request too large … OTPM: Limit 1000"). Its reasoning replies need 1,000–2,200 output tokens, so many retries are refused.
- **Requests that fit do succeed.** 4 calls at 13:25–13:28 used 1,227–2,200 completion tokens each.
- **Tokens per day: 200,000**, shared org-wide per model. By 14:42 **both** gpt-oss-120b and Qwen had hit **TPD 200k** (Used ~198k).
- Consequences:
  - In the 14:42 data cycle, **6 of 12 judge calls failed with TPD 429**. The 4 new tasks (both new missions) were scored mostly by Flash-Lite, the lenient judge. Re-score them tomorrow: `uv run evolvra score --mission <id> --rescore`.
  - Qwen answered **7/12** tasks in the final re-score, 4/12 before my fixes.
- Day totals in `provider_usage`: groq 180 requests / 458k tokens, gemini 176 / 457k.
- Suggestions, your call:
  - Qwen with `reasoning_effort: "none"`, if Groq supports it for 3.8. Untested, not changed.
  - Or a non-reasoning third judge.
  - A per-task guard: don't use a task in fitness or evolution unless ≥2 judges answered.

### New missions (REVIEW 6)
| mission | builder | builder attempts | QA | QA evidence | fitness |
|---|---|---|---|---|---|
| `…104040-build-a-single-file` | rapid-prototyper | 1, PASS | 1, PASS | own static checks; true 375px viewport via CDP `Emulation.setDeviceMetricsOverride` (scrollWidth 360 desktop / 375 mobile, 1 column), 1280px one row; 0 network requests; target SHA unchanged | 0.881 |
| `…104658-write-a-user-interview` | ux-researcher | 1, PASS | 1, PASS | own `verify_guide.py`: 5 questions, 10 probes, 0 banned openers, minutes 42 ≤ 45; read by hand; 5 low optional issues | 0.605 (truncation, see above) |

- Both personas have all tools (no `tools:` line), so execution criteria stayed on the builder too.
- The builder of mission A found that headless Edge won't size a window below ~492px and measured inside iframes. QA confirmed this with a control run and used a real 375px viewport.
- Both missions ran in this session. Agent definitions and the hook were loaded at session start (pre-0.3.0), so **the new `off_record` hook flag was not active**. All work went through `task start` and nothing was resumed.

### Answers to your open questions
- **Qwen and 8k TPM:** the binding limits are Qwen's **1k OTPM** and the **200k TPD** per model, not the 8k TPM. See above.
- **`"reopened": [..]` after restart:** not tested. No natural QA failure, and Claude Code has not been restarted yet. The recorder prints `"reopened": []` on PASS, so the field is there.

### Open questions / for you
1. Judge-input truncation (above): which option?
2. Qwen: `reasoning_effort: none`, a different third judge, or a min-judges guard?
3. Bank tasks whose criteria require execution: exclude them from the arena, or rewrite them for a non-executing actor?
4. The scheduled `-Evolve` run fires at **16:17 today** with Groq at its daily cap. The mutator is gpt-oss on Groq, so I expect it to produce no candidates (harmless). I left the task enabled. Youssef can skip today's run if you prefer.
5. Youssef: **restart Claude Code** so 0.3.1 (v2 persona, `off_record` hook, new SKILL.md) is live.

### Still not verified
- `/evolvra:mission` behaviour after the restart, and `reopened` on a real QA failure.
- Whether the scheduled task logs correctly with the new logger. The first real test is the 16:17 run; check that `cycle.log` gets UTF-8 lines at ~16:17.
- Re-scoring the 4 newest tasks with all 3 judges (Groq TPD resets).
