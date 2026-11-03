# Operator status (written by the local Claude Code session at the end of every working session)

## Session 2026-11-03 (11:42–12:40 AST, local operator, Opus 5.5, zero spend)

### REVIEW.md items
| # | item | state |
|---|---|---|
| 1 | finish mission 3 | **done** (it was already finished by the other tab at 11:24; record has a gap, see item 7) |
| 2 | `cycle.ps1 -Evolve` + report | **done**, numbers below |
| 3 | audit one arena task by hand | **done**, judge bias found (below) |
| 4 | frontend-developer + sprint-prioritizer missions | **done**, both PASS first attempt, QA-verified |
| 5 | don't touch weights / judges / margins | respected; nothing changed. Recommendations below are for you |
| 6 | refresh installed plugin | **done via CLI**, restart still pending (below) |
| 7 | write the exact mission-3 sequence | **done** (below) |

### Ran
- `uv run pytest -q` → 43 passed, then 44 passed after my fix; `uv run ruff check .` → clean.
- `.\scripts\cycle.ps1 -Evolve` 11:45:01 → **1409 s wall clock (23.5 min)**.
- `evolvra score --mission 20261103-080434-propose-three-zero-budget --rescore` after the scorer fix.
- `claude plugin marketplace update evolvra` + `claude plugin update evolvra@evolvra`.
- Missions `20261103-091344-build-a-small-accessible` and `20261103-092430-rank-a-12-item`.
- `.\scripts\cycle.ps1` (data only) 12:30:46 → **255 s**.

### Evolution generation (`20261103-085247-evidence-collector`)
```
ingest: missions added=3 updated=1 | traces added=116 skipped=15
score: tasks scored=6 | judge calls=18 cached=0 errors=2
evolve: no promotion: parent evidence-collector v1 fitness=1.0; best paired delta +0.0 on 3 shared task(s) is below the margin
```
| persona | target | proxy fitness | paired delta | coverage |
|---|---|---|---|---|
| parent v1 | – | 1.0 | – | 3/3 |
| candidate 1 | missing_required_content | 1.0 | 0.0 | 3/3 |
| candidate 2 | missing_required_artifacts | 0.9683 | −0.0317 | 3/3 |
| candidate 3 | missing_feature_status_labels | 0.95 | −0.05 | 3/3 |

- No promotion. All 3 candidates passed lint.
- **Provider requests in this cycle**: these are new `llm_cache` rows, so failed calls are not counted. Gemini Flash-Lite 30, Gemma 16, Groq gpt-oss-120b 21 = **67**. Of these, 19 were mission scoring and 48 were evolution (mutator, actor and arena judges).
- **`provider_usage` at the end of the session (whole day)**: groq 66 requests / 145k tokens, gemini 125 / 259k.
- **Timing**: the 23.5 min breaks down into about 7 min scoring 6 tasks (11:45→11:52) and about 15 min of evolution (11:52→~12:08).

### Arena audit (REVIEW 3): the judges have a ceiling problem
I read `arena/parent/task-1.md` and `arena/candidate-3/task-1.md` side by side (bank seed "login bug verification checklist").
- **The two outputs are near-identical in substance.** Both meet all 3 criteria. Candidate 3 is arguably the better one: it adds console logs and states honestly that it has no tool access. The parent asserts "as captured in previous incident reports" and assumes `laravel.log`, both invented.
- **The scores disagree with that.** The ensemble gave the parent 1.0 and candidate 3 0.93, because it marked candidate 3 down on evidence (0.7). The 0.07 gap is noise, possibly penalising the honesty notice.
- **Per-judge scores from `llm_cache`, this cycle's arena plus re-score**:
  - `gemini-3.5-flash-lite` returned 1.0/1.0/1.0/1.0 in **13 of 14** responses. The other one was all-zero.
  - `gemma-4-31b-it` returned 1.0/1.0/1.0/1.0 in **9 of 9** parsed responses.
  - `openai/gpt-oss-120b` is the only judge that discriminates: evidence 0.1–0.9, correctness 0.2–1.0.
- **The median hides real failures.** Parent task 3: gpt-oss scored correctness 0.4 and evidence 0.2, with failure `fabricated_evidence` ("fabricates command outputs and file contents"). The two Gemini-hosted judges gave 1.0, so the median is 1.0. The report then prints the minority critique next to a perfect score.
- **Consequence:** with a median of 3 and two judges stuck at 1.0, the parent hits the ceiling and no candidate can ever clear the +0.03 margin. Evolution of the weakest agent is impossible on this bank and judge set.
- **The bank is only the 3 seed tasks** (`evolvra bank evidence-collector`). No mission-derived tasks were used, presumably filtered as not self-contained because QA tasks reference the builder's files. The arena never tests what this agent actually scores badly on: real-mission fitness is 0.28–0.99, mean 0.751.
- Not changed (you own these). Suggestions:
  - (a) drop or replace one Gemini-hosted judge, or use mean/min instead of median for `evidence`;
  - (b) self-contained QA bank tasks that embed the builder's output inline;
  - (c) make the reported critique come from the judge whose scores are closest to the median.

### Gemma is unreliable as a judge
`rubric:error` rows today are all `gemini/gemma-4-31b-it`:
- In the data cycle it failed **4/4** calls: HTTP 500 ×3 and unparseable ×1. Earlier today there were further HTTP 500, 503 ("high demand") and unparseable errors.
- New tasks are therefore effectively scored by 2 judges.

### What broke / surprised me
1. **Scorer showed the judges a virtualenv instead of the deliverable** (fixed, `20814d5`).
   - Mission 3's QA created `.venv` inside `02-evidence-collector`.
   - `checks.output_files` skipped hidden *files* but not files inside hidden *directories*. Sorted `rglob` put about 11k `.venv` files first, and the 20-file cap filled with `dateutil` sources.
   - So the judges never saw `QA-REPORT.md`, and evidence-collector scored **0.2** on that task ("unrelated code files").
   - After the fix plus `--rescore`, the score is **0.575**. Fitness table after both cycles: evidence-collector 0.751 (6 tasks), backend-architect 0.777, everyone else 0.988–0.995 (1 task each).
2. **The installed plugin was stale** (`0.1.0` cache from `06c840c`: no `task reopen`, old SKILL.md). This is the root cause of item 7.
3. **`cycle.log` "cycle end" reused the start stamp**, so durations were unreadable (fixed, `bc5aae2`). The data cycle now logs `12:30:46 start / 12:35:01 end`.
4. **Some personas cannot run commands.** The sprint-prioritizer persona has no shell tool (Read/Write/Edit/Web only), and neither do growth-hacker and content-creator. It wrote `rice_score.py` but had to hand-write `ranking_output.csv`. It said so honestly.
   - I (orchestrator) ran `rice_score.py --check` read-only: CHECK OK, exit 0, recorded transparently in the task evidence.
   - QA then reran it in a sandbox: byte-identical SHA256, plus negative controls.
   - Briefs with "reproducible / run a check" criteria can't be self-verified by these personas. Should they get Bash, or should such criteria go to QA only?

### REVIEW 7: exact mission-3 sequence (from `traces.jsonl`, local time; record left untouched)
1. **11:04:36** `start`, tasks added, `task start 1`. 11:04:48 Agent growth-hacker → handback 11:07:48.
2. **11:07:58** `task done 1 --verdict PASS`, `task start 2`. 11:08:17 Agent evidence-collector → handback 11:16:29 with NEEDS_WORK.
3. **11:16:40** `task done 2 --verdict NEEDS_WORK`. The orchestrator then "checked recorder options": the installed 0.1.0 recorder had no `reopen`. `f5d9ced` (which adds it) landed at 11:20:25, during the rework, and was never installed in that tab.
4. **11:16:50** copied the attempt-1 `EXPERIMENTS.md` aside. **11:17:14** `SendMessage` *resumed the existing growth-hacker agent*; it was not re-launched through `task start 1`. Its edits ran 11:20:11–11:21:04. These traces have `task_no: null`, because no task was running in `current.json`.
5. **11:21:11** `task start 2` (QA attempt 2). 11:21:28 `SendMessage` resumed the QA agent → PASS at 11:24:16. `finish done`.

**Net effect on the record**
- growth-hacker shows 1 attempt PASS: efficiency 1.0, fitness 0.988, overstated.
- evidence-collector shows 2 attempts: efficiency 0.5 for a retry caused by the *builder*.

**Hardening ideas (yours to pick)**
- (a) `task start <qa> ` for attempt ≥2 refuses unless a dependency was reopened since QA's last attempt.
- (b) `task done <qa> --verdict NEEDS_WORK|FAIL` auto-reopens the builder dependencies.
- (c) The trace hook warns when a mission is active but `task_no` is null (work happening off the record).
- (d) The skill should say "relaunch via `task start`, never resume an agent with SendMessage".

### REVIEW 6: plugin refresh
- **Done:** `claude plugin marketplace update evolvra` → ok. `claude plugin update evolvra@evolvra` → "updated from 0.1.0 to 0.2.0 … Restart to apply changes".
- **Verified:** `installed_plugins.json` points to `cache/evolvra/evolvra/0.2.0`, and its `scripts/mission.py` is byte-identical to the repo's (`cmp`) with `reopen` present.
- **Not verified:** that `/evolvra:mission` uses `task reopen` after a restart. I can't restart my own session, so Youssef needs to restart Claude Code. Neither new mission hit a QA failure, so `reopen` was not exercised.
- Today's two missions used the repo recorder `plugin/scripts/mission.py`, which is identical to 0.2.0, and followed the 0.2.0 SKILL.md.

### New missions (REVIEW 4)
| mission | builder | builder attempts | QA | QA evidence | fitness |
|---|---|---|---|---|---|
| `…091344-build-a-small-accessible` | frontend-developer | 1, PASS | 1, PASS | own headless-Edge run 25/25, contrast 8/8, axe-core 0 violations | 0.995 |
| `…092430-rank-a-12-item` | sprint-prioritizer | 1, PASS | 1, PASS | independent recompute 92/92, byte-identical rerun, 3 negative controls | 0.988 |

- **Mission A, not tested:** real screen-reader speech. A possible double announcement (radio + live region) is flagged as low.
- **Mission B:** a stale "not executed yet" note remains in its section 6 (low).

### Changed (commits on `main`)
- `20814d5` Scorer: skip `.venv`, `node_modules`, `__pycache__`, `site-packages`, `venv`, `env` and any dot-directory when collecting output files. Failing test first (`test_output_files_skip_virtualenvs_and_hidden_dirs`), then fix; 44 passed, ruff clean.
- `bc5aae2` `cycle.ps1`: end line stamped with the end time.
- `1bc528c` (by the cycle) data refresh, 6 missions.
- This STATUS.md.

### Answers to your open questions
- **`-Evolve` wall clock:** 1409 s (23.5 min) with 6 tasks to score; about 15 min of that is the evolution generation. A data-only cycle with 4 new tasks takes 255 s.
- **Scheduled task while locked:** "Evolvra Cycle" runs `cycle.ps1 -Evolve` with LogonType *Interactive*, last run 10:17:44 with result 0, next 16:17:44.
  - Interactive tasks run while the user is signed in, and a locked screen is still signed in. So it *should* fire while locked, but not after sign-out or while asleep.
  - **Not verified:** `cycle.log` has no record of the lock state. A clean test: lock the laptop before 16:17 and check for a `cycle start` line at ~16:17 tonight.

### Open questions
1. Judges: replace or down-weight a Gemini-hosted judge, and/or drop Gemma (unreliable)? Without that, arena fitness saturates at 1.0.
2. Bank for QA agents: add self-contained tasks that embed the artefact to verify?
3. Should a QA retry caused by the builder count against QA's `det:efficiency`?
4. Shell access for growth-hacker / content-creator / sprint-prioritizer, or keep "run a script" criteria off their tasks?
5. Mission 3's record overstates growth-hacker. Leave it as is (done, per item 7), or add a recorder `note` command to annotate records without editing them?
