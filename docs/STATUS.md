# Operator status (written by the local Claude Code session at the end of every working session)

## Session 2026-11-03 evening (15:13–16:30 AST, local operator, Opus 5.5, zero spend)

### REVIEW.md items (round 3, 12:45Z version)
| # | item | state |
|---|---|---|
| 1 | pull, `score --rescore`, fitness before/after | **partial.** 7 of 16 tasks re-scored before Groq TPD 429s. I stopped, as instructed. Only 4 tasks have a full 3-judge result. Details below |
| 2 | three missions with `evidence-collector` QA | **done.** content-creator, backend-architect, devops-automator: all PASS first attempt, QA by **v2**. v2 fitness is provisional (1 judge) |
| 3 | judge reliability, candidate pings | **done.** Qwen 31% raw (71% without quota errors). After `910be39` every Qwen failure was a quota 429. Both candidates answered **HTTP 503** twice |
| 4 | UX Researcher discrepancy | **done.** QA was right about the builder. The judges were wrong (truncation). Paragraph below |
| 5 | 16:17 run fired? | **fired** 16:17:48, `LastTaskResult=0`, UTF-8 lines in cycle.log. Lock state not provable, see below |
| 6 | let the scheduler pick the target | respected. No manual `-Evolve`. The 16:17 run picked ux-researcher itself |
| 7 | no weight/judge/margin/actor changes | respected. One router fix (`bc47cd9`), test-first, reason below |

### Ran (in order)
- `git pull --rebase` → `910be39`. `uv run pytest -q` **57 passed**, `ruff check .` clean.
- `evolvra fitness` (the "before" table below); `evolvra providers`; `evolvra ping groq` and `--model qwen/qwen3.8-27b` (both `pong`).
- `evolvra score --rescore` 15:15 → stopped 15:40 (TPD 429s, see item 1).
- Missions via `/evolvra:mission` (plugin 0.3.1, cache files `cmp`-identical to the repo):
  `20261103-121621-write-a-launch-blog`, `20261103-122155-build-a-stdlib-only`, `20261103-122908-write-a-backup-rotation`.
- Router fix, tests **58 passed**, ruff clean, pushed `bc47cd9`.
- Waited for the scheduled `cycle.ps1 -Evolve` (16:17:48 → 16:19:27, pushed `498ba33`).
- `evolvra ping gemini --model gemini-3.6-flash` / `gemini-3.7-flash`, twice each (15:58 and 16:22).

### Item 1: re-score with whole-deliverable judge input
The re-score did tasks 1–7 in order, then Groq refused with **TPD 429** on both models:
- gpt-oss: "Used 199054 of 200000 … try again in 30m43s"
- qwen: "Used 198036 … 26m48s"

Groq's TPD is a **rolling** window, not a midnight reset: the wait shrinks as old usage ages out. So "finish tomorrow" really means "after ~10:30 AST tomorrow", when this morning's heavy use leaves the window. Run it then.

**Tasks with a full 3-judge result before and after** (these are the real evidence for the truncation fix):

| task | agent | correctness before → after | failure class after |
|---|---|---|---|
| 1 one-paragraph | content-creator | 0.975 → 1.00 | none |
| 2 its QA | evidence-collector v1 | 0.475 → **0.675** (2 → 3 judges) | missing_acceptance_detail |
| 3 REST API | backend-architect | 0.815 → 0.84 | (scored again by the 16:17 cycle) |
| 5 GitHub Actions | devops-automator | 0.815 → **0.59** | `invalid_yaml_syntax`, **which is false**, see below |

**Fitness per agent.** Before = the table at the start of this session (the "after" column of the pm STATUS). Now = after the partial re-score, the 16:17 cycle and the 3 new missions.

| agent | before | now | why it moved |
|---|---|---|---|
| ux-researcher | 0.605 | 0.605 | not re-scored yet; still the truncated 2-judge verdict |
| devops-automator | 0.830 | 0.832 | GH task fell to 0.663 (Qwen error); new rotation task 1.00 (1 judge) |
| rapid-prototyper | 0.881 | 0.881 | not re-scored |
| evidence-collector v1 | 0.860 | 0.910 | 5 of its 8 tasks are now **1-judge** (Flash-Lite) |
| backend-architect | 0.848 | 0.943 | REST task 3 judges; new limiter task 1 judge |
| growth-hacker | 0.882 | 0.988 | **1 judge only**, provisional |
| content-creator | 0.968 | 0.978 | |
| sprint-prioritizer | 0.970 | 0.970 | not re-scored |
| frontend-developer | 0.975 | 0.975 | not re-scored |
| **evidence-collector v2** | — | **0.988** (3 tasks) | all 3 tasks 1-judge, provisional |

**Important:**
- **A 1-judge ensemble counts fully in `fitness`.** `910be39` only makes such tasks pending again; `fitness` and evolution still use them now.
- **My re-score made 4 tasks *worse* as data.** Tasks 3, 4, 6 and 7 had 3-judge ensembles before. When the Groq judges failed, the re-score replaced them with 1-judge Flash-Lite ensembles. Task 3 is back to 3 judges; tasks 4, 6 and 7 are still 1-judge.
- **These scores are provisional.** All 1-judge tasks are pending and will be re-scored when Groq has room (the 22:17 run will try).
- Flash-Lite alone gives 1.0 to almost everything, which is why growth-hacker, evidence-collector and v2 look so high. **Don't read the "now" column as a result yet.**
- Suggestion (your call): `fitness` should ignore or down-weight ensembles with fewer than `MIN_JUDGES` judges, or `--rescore` should keep the old row when fewer judges answer than before.

**Task 5 audit: Qwen made a factual error, and the trimmed-low mean amplified it.**
- Qwen said `"on": push` is invalid YAML. It is valid: quoting `on` is the usual guard against YAML 1.1 reading it as a boolean.
- QA saved `raw-actionlint.txt`: actionlint 1.7.7 "Found total 0 errors", exit 0. A negative control fails as expected.
- The three verdicts were Flash-Lite 1.0, gpt-oss 0.68, Qwen 0.5. The trimmed-low mean drops the top judge and averages (0.68 + 0.5) / 2 = **0.59**. It also takes Qwen's failure class.
- So with whole files visible, one wrong low judge now drives the score. That is the mirror image of the old "two lenient judges" problem. Data for your judge decision.

### Item 2: Evidence Collector v2 on real missions
| mission | builder (attempts, minutes) | QA v2 (attempts, minutes, tool events) | QA's own checks | raw files under `evidence/` |
|---|---|---|---|---|
| launch blog post (no-shell builder) | content-creator 1, 2.5 | 1, 2.4, 10 | own `verify_post.py`: 5 word-count methods 769–865, 4 closed code blocks, 0 quote marks, 1 CTA; tested itself on planted fake social proof | 2 |
| stdlib token-bucket limiter | backend-architect 1, 2.1 | 1, 4.8, 18 | 11 builder tests ×20 runs; **23 own adversarial checks**; mutation test 5/7 killed; found 3 low test-quality gaps | 12 |
| PowerShell backup rotation | devops-automator 1, 3.1 | 1, 6.5, 26 | self-test re-run on 5.1; **38 own edge checks** (ISO week 53, gaps, read-only/locked files); ISO-week function vs reference for 14,976 days, 0 mismatches; 3 mutants all caught | 9 |

- **Fitness:** v2 **0.988** on 3 QA tasks vs v1's 0.86. **Not a valid comparison yet**: all three v2 tasks were judged by Flash-Lite alone, because Groq was at its cap. Decide after these 3 tasks have ≥2 judges (pending, re-scored automatically).
- **"Raw Evidence Files" section:** **0 of 3** reports have a section with that exact title. **3 of 3** saved real raw output under `evidence/` and cite those files in every table row (VERIFICATION.md line 6; a "Raw evidence file(s)" column in criteria_table.md; inline `evidence/0N` refs in verification-table.md). The substance is there; the heading the persona asks for is not.
- **Slower?** Somewhat. v2 QA took 2.4 / 4.8 / 6.5 min (mean 4.6). v1 first attempts took 0.8–8.7 min (mean 3.8, median 3.4, n=8). v2 also uses more tool events: median 18 vs v1's median 8. Most of the extra time is real extra checking (adversarial tests, mutants), not waste. n=3, so treat this as a hint.
- **Off-record work:** **0**. All 89 trace events of the 3 missions carry `off_record: false`. 6 SubagentStop events, all inside `task start`. This is the first run with the 0.3.1 hook live.
- v2 also reported its own mistakes honestly: a superseded mutation run, two harness-bug runs, all kept as raw files. It also corrected a builder's claim ("19 checks"; the self-test prints 16 PASS lines).
- Builder-side notes from QA (not defects against the criteria):
  - limiter: `retry_after` under-reports after an injected clock jumps backwards
  - rotation: read-only backups are deleted via `-Force`, which the README doesn't mention

### Item 3: judge reliability (current score rows created today)
| judge | verdicts | errors | quota 429 | other | raw | without quota |
|---|---|---|---|---|---|---|
| gpt-oss-120b (Groq) | 14 | 12 | 12 | 0 | 54% | 100% |
| qwen3.8-27b (Groq) | 10 | 22 | 18 | 4 | **31%** | 71% |
| flash-lite (Gemini) | 22 | 0 | 0 | 0 | 100% | 100% |

- **Qwen's 4 "other" errors are all unparseable replies from 09:59–10:39Z, before `910be39`.** Since then, every Qwen failure is a quota 429 (14 TPD, 4 OTPM).
- **`reasoning_effort: "none"` works.** Groq accepted it. Qwen's completion tokens dropped from 1,227–2,200 (pm) to **239–620** per verdict (llm_cache, 12:15–12:27Z).
- **So Qwen's remaining problem is not reliability but budget.** It shares Groq's 200k TPD per model, and judge prompts are now 5–8k tokens because files are no longer cut.
- **Candidates:** `gemini-3.6-flash` and `gemini-3.7-flash` both returned **HTTP 503 "model is currently experiencing high demand"**, at 15:58 and 16:22 AST. Each `ping` already retries a 503 once. Wall time was 8–25 s to fail. No `pong`, so no latency figure. I changed nothing.
- Data for your decision: a third judge on **Gemini** would spread load away from Groq's TPD. gemma-4-31b-it (old judge, Gemini) logged 4 verdicts / 9 errors today (6× HTTP 500/503, 3 unparseable), so it is not a good fallback either.

### Item 4: who was right about the UX interview guide?
**QA was right about the builder; the judges were wrong, and only because of truncation.**
- The guide (14,768 chars) meets all three criteria. I read it myself:
  - exactly 5 main questions, opening with Walk / Tell / Think / How / Tell, 2 probes each
  - inclusion I4 "at least 3 separate days within the first 7 days" (a count plus a time window), 5 exclusions, target 12 with a saturation justification
  - 8 timed sections summing to 42 ≤ 45
  - a 5-row "why it is not leading" table
- QA's own `verify_guide.py` output confirms each of these with line numbers.
- The judges' critiques show why they disagreed:
  - gpt-oss: "the provided excerpt does not show the list of main questions"
  - Flash-Lite: "the output file was truncated mid-text"
  - Qwen: errored
  - Both scored criteria they could not see as unmet. `910be39` fixes this.
- **QA was not lenient on the builder, but it was incomplete on its own task.** Its criterion 1 asked for a per-criterion PASS/FAIL table with quoted lines. That table lives only in its chat reply (mission.json evidence); the files have the script and raw output but no table. The 16:17 cycle re-judged task 16 with whole files, and Flash-Lite flagged exactly that (0.5, `missing_required_element`).
- That was v1. All three v2 reports saved a table file, so v2 already does this.
- Builder task 15 still sits at **0.45 / fitness 0.605**: it had 2 judges, so `910be39` does not re-pick it. It needs an explicit `uv run evolvra score --mission 20261103-104658-write-a-user-interview --rescore` once Groq has room.

### Item 5: the scheduled runs
- **16:17 run fired:**
  - Task Scheduler: `LastRunTime 16:17:45`, `LastTaskResult 0`, next run 22:17:44.
  - cycle.log (UTF-8, readable): `16:17:48 cycle start (evolve=True)` … `ingest: missions added=3 updated=8 | traces added=163`, `score: tasks scored=12 | judge calls=36 cached=4 errors=22`, `evolve: no promotion: parent ux-researcher v1 fitness=0.9417; no candidate completed enough shared tasks`, `push: ok`, `16:19:27 cycle end`.
- **Lock state:** I could not prove the laptop was locked. No lock/unlock events (4800/4801) were in the Security log for the last 2 h; lock auditing may simply be off. This session was active at the time. The task's LogonType is `Interactive`, so it runs while Youssef is signed in, locked or not.
- **Evolution:** ux-researcher was picked as weakest because of the stale 0.605. The mutator is gpt-oss on Groq, which was at its cap, so the generation made no usable candidates. This is harmless, as you predicted for this case.

### What broke, and what I changed
1. **`bc47cd9` Router: a 429 that asks for more than 90 s fails fast; `26m48s` is parsed.**
   - The problem:
     - Groq's TPD 429 says "try again in 26m48.768s". The regex only knew `Ns` and `Nms`.
     - `_send` slept the 90 s maximum twice per judge anyway.
     - Re-score tasks 3, 4, 6 and 7 took **~6 min each** doing nothing useful: 12:21, 12:27, 12:33, 12:39Z.
   - The fix:
     - Waits in h/m/s/ms are parsed.
     - A 429 asking for more than `MAX_429_WAIT_S` (90 s) raises immediately.
     - Per-minute 429s still wait and retry as before.
   - Test first: `test_429_with_a_long_wait_fails_fast` uses Groq's real message and failed with 3 attempts before the fix. Tests 57 → 58.
   - Effect: the 16:17 cycle scored 12 tasks with 22 judge errors in **1 min 39 s**, not about an hour.
   - Why this is not a judge or budget change: same judges, same max_tokens, same retry count for per-minute limits. It only stops sleeping when the wait could not succeed anyway.
2. **My re-score degraded 4 tasks from 3 judges to 1** (see item 1). Nothing was edited by hand; they re-score automatically.

Commits this session: `bc47cd9` (router fix), `498ba33` (scheduled cycle, data), plus this STATUS commit.

### Answers to your open questions
- **Groq per-day cap (800 requests):** not close. Today 230 requests, 481k tokens. **The binding cap is TPD: 200k tokens per model.** gpt-oss and Qwen both sat at ~198–199k from ~14:40 AST until at least 16:17. Whole-file judge prompts (5–8k tokens each) reach it faster than the 4k-per-file prompts did.
- **Duration of the data-only cycle for 2 new missions, 3 judges:** 14:42:19 → 15:04:05, **1308 s (22 min)** (pm session). Much of that was 429 sleeps that `bc47cd9` now skips when the wait is long.

### Open questions / for you
1. Should `fitness` (and the evolution target pick) ignore ensembles with fewer than 2 judges? Right now Flash-Lite-only rows inflate v1, v2, growth-hacker and backend-architect.
2. Should `--rescore` keep the existing row when fewer judges answer than last time? It replaced 3-judge rows with 1-judge rows today.
3. Third judge: Qwen is reliable when it has budget, but it shares Groq's TPD with gpt-oss. Both Gemini candidates were 503. Try again tomorrow, or another model?
4. Trimmed-low mean plus one factually wrong low judge (task 5) gives 0.59 for a workflow that passes actionlint. Is that acceptable?
5. The v2 persona asks for a section titled "Raw Evidence Files". v2 delivers the substance (real files, cited per row) but not the heading. Do you want the heading enforced, or is per-row citation enough?

### Still not verified
- v2 vs v1 with ≥2 judges (needs Groq budget).
- The UX builder re-score with whole files (needs an explicit `--rescore` of that mission).
- `reopened` on a real QA failure: all 6 tasks today passed on the first attempt.
- Whether a run fires while the screen is actually locked: needs a lock-event log, or Youssef locking the laptop before 22:17.
