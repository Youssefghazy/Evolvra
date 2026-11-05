# Operator status (written by the local Claude Code session at the end of every working session)

## Session 2026-11-05 (10:20–11:25 AST, local operator, Opus 5.5, zero spend)

### REVIEW.md items (round 5, "finish line")
| # | item | state |
|---|---|---|
| 1 | pull, plugin check, tests | **done.** `68d90cc`. Plugin unchanged (0.3.1, no `plugin/` diff), so no refresh. **60 passed**, ruff clean |
| 2 | fix the stale UX score | **done.** ux-researcher **0.605 → 0.922** (2 → 3 judges, 0 errors). Tables below |
| 3 | OpenRouter third judge | **done (report only).** Key present. Two non-OpenAI free models answer `pong`: NVIDIA Nemotron-3-ultra and Cohere north-mini-code. Both Gemma models gave upstream 429. Judge set unchanged |
| 4 | real QA-failure retry | **both item-4 missions passed first time** (not forced). **The retry came in item 5** (growth-hacker): `"reopened": [1]`, builder attempt 1 `FAIL` + `reopened_by_qa: true`, QA attempt 2 `PASS` + `caused_by_builder: true` |
| 5 | growth-hacker + sprint-prioritizer missions | **done.** growth-hacker PASS after 1 QA-driven retry; sprint-prioritizer PASS first attempt |
| 6 | `cycle.ps1 -Evolve` once | **done.** Manual run: evolve **skipped** (last generation 0.9 h before). The scheduled 10:21 run did evolve: ux-researcher, 3 candidates, no promotion. Details below |
| 7 | STATUS + still broken / unproven | this file; one-line answer at the end |

### Ran (in order)
- `git pull --rebase` → `68d90cc`. `uv run pytest -q` **60 passed**, `uv run ruff check .` clean. `evolvra providers`, `evolvra fitness` (the "before" table).
- The **scheduled 10:17 `cycle.ps1 -Evolve` was already running** when I started. It held the DB lock, so my first `ping groq` failed with `database is locked`. Its own `git pull` raced mine (`cannot lock ref 'refs/remotes/origin/main'`), which was harmless: the tree was already at `68d90cc`. It finished at 10:25, ran a ux-researcher generation (no promotion) and pushed `742d240`. I waited for it before touching the DB.
- `evolvra ping groq` → `pong`. `evolvra score --mission 20261103-104658-write-a-user-interview --rescore` (8 s), then `evolvra fitness`.
- `evolvra models openrouter`, then pings with `--model` (item 3).
- Four missions via `/evolvra:mission` (plugin 0.3.1): `20261105-072406-write-a-product-announcement`, `20261105-073059-build-a-single-file`, `20261105-074515-design-a-referral-loop`, `20261105-080841-rank-10-bugs-of`.
- `.\scripts\cycle.ps1 -Evolve` 11:12:10 → 11:16:45, pushed `de2364a`.

### Item 2: UX builder re-score
| | judges | correctness | completeness | evidence | quality | fitness |
|---|---|---|---|---|---|---|
| before (3 Nov 11:57, truncated input) | gpt-oss + Gemini (Qwen errored) | 0.45 | 0.50 | 0.25 | 0.65 | **0.605** |
| after (5 Nov, whole file) | gpt-oss + Qwen + Gemini | 0.90 | 0.90 | 0.90 | 0.88 | **0.922** |

Per judge after: gpt-oss 0.85/0.9/0.9/0.88, Qwen 0.9/0.9/0.8/0.85, Gemini 1.0/1.0/1.0/0.9. Six calls, 3 cached (the QA task kept its stronger ensemble at 0.71, as round 4 rule 2 requires), 0 errors.

**Fitness before → after this session** (the "after" column also includes the 4 new missions, scored by the 11:12 cycle; every row has ≥2 judges):

| agent | ver | before (tasks) | after (tasks) |
|---|---|---|---|
| devops-automator | 1 | 0.805 (2) | 0.805 (2), **now the weakest** |
| backend-architect | 1 | 0.863 (2) | 0.863 (2) |
| evidence-collector | 1 | 0.880 (8) | 0.880 (8) |
| rapid-prototyper | 1 | 0.881 (1) | 0.923 (2) |
| evidence-collector | 2 | 0.886 (3) | **0.924 (7)** |
| growth-hacker | 1 | 0.915 (1) | 0.903 (2) |
| ux-researcher | 1 | **0.605 (1)** | **0.922 (1)** |
| content-creator | 1 | 0.965 (2) | 0.915 (3), see "judge miscount" below |
| sprint-prioritizer | 1 | 0.970 (1) | 0.956 (2) |
| frontend-developer | 1 | 0.975 (1) | 0.975 (1) |

v2 vs v1 with the extra data: **evidence-collector v2 0.924 (7 tasks) vs v1 0.880 (8 tasks)**. The promotion still stands, and the gap has widened.

### Item 3: OpenRouter
- `providers` shows the OpenRouter key present (I did not open or print `.env`). `models openrouter` lists 421 ids. **Warning from the CLI: the default `openai/gpt-oss-120b:free` is not in the list**, so `EVOLVRA_MODEL_OPENROUTER` would need setting before it can be used. I left it unset: the judge set is your call.

| model | result | latency |
|---|---|---|
| `nvidia/nemotron-3-ultra-550b-a55b:free` | `pong` (finish=stop, 51 tokens) | 2.8 s |
| `cohere/north-mini-code:free` | `pong` (finish=stop, 44 tokens) | 3.1 s |
| `google/gemma-4-31b-it:free` | HTTP 429, "rate-limited upstream" (shared Google AI Studio pool), twice | 45.6 s / 45.7 s |
| `google/gemma-4-26b-a4b-it:free` | HTTP 429, same upstream message | 45.1 s |

5 of 40 local OpenRouter calls used. The Gemma 429s took ~45 s each, because the router retries an upstream 429 that gives no retry-after. Note: north-mini-code is a code model, so it may be a weak prose judge. Nemotron-3-ultra is the stronger candidate.

### Items 4 + 5: missions
| mission | builder | attempts | QA | result |
|---|---|---|---|---|
| product announcement (3 × 90–110 words, adjective-free first sentences, 2 features) | content-creator | 1 | v2, PASS | 101/104/104 words (QA script + my own count agree), 0 adjectives, features "Flow Sync" and "Recall Search" |
| HTML pricing mock (<6 KB, 0 external, 3 cards, 1 keyboard toggle) | rapid-prototyper | 1 | v2, PASS | 4038 B, 0 external requests (grep + headless network log), CDP keyboard test 11/11, **html-validate 11.18.0: 0 errors** (negative control: 8 errors). I re-ran the validator myself: exit 0 |
| referral loop with fraud-risk section | growth-hacker | **2** | v2, **NEEDS_WORK → PASS** | QA attempt 1 failed C5: 6 assumed numbers untagged, and the header claimed they were all tagged. Builder reopened, added A15–A27; QA attempt 2: 27 tags = 27 rows, 0 untagged |
| RICE ranking of 10 bugs | sprint-prioritizer | 1 | v2, PASS | 114 checks, 0 failed; 10/10 scores recomputed; tie rule verified |

The record for the retry (`mission.json`, via the recorder only):
- `task done … 2 --verdict NEEDS_WORK` printed `"reopened": [1]`.
- Task 1 attempts: `{n:1, verdict: FAIL, reopened_by_qa: true}`, then `{n:2, verdict: PASS}`.
- Task 2 attempts: `{n:1, NEEDS_WORK}`, then `{n:2, PASS, caused_by_builder: true}`.
- The scorer saw it: growth-hacker's `det:efficiency` is **0.5** on that task (1.0 on every other new task).

Both item-4 missions passed first time, and I did not force a failure. The tight criteria were met: content-creator wrote very plain first sentences, and rapid-prototyper produced clean HTML.

### Item 6: evolution
- **Manual run 11:12:10–11:16:45 (275 s):** ingest 4 missions / 120 traces, scored 8 tasks (24 judge calls, **1 error**: Gemini HTTP 503 on the RICE QA task, which therefore has 2 judges), `evolve: skipped, last generation ran 0.9h ago`, exported, pushed `de2364a`. That makes 275 s the wall-clock of an effectively data-only cycle with 8 tasks to score. Cycles with nothing new took 20–90 s in cycle.log.
- **Scheduled 10:21 run (generation 8):**
  - Target ux-researcher. It was chosen on the stale 0.605 before my re-score; its bank parent fitness was 0.9033.
  - 3 candidates:
    - `missing_required_content`: 0.8967, Δ −0.0067
    - `weak_evidence`: 0.899, Δ −0.0043
    - `missing_acceptance_criteria_check`: 0.9133, Δ **+0.01**
  - All on 3 shared tasks. Margin 0.03, so **no promotion**.
- **Generation 8 is byte-identical to generation 7** (22:17 yesterday): same 3 candidate SHAs (`4cbfe1d780`, `13cef41d01`, `45fe0c606a`), same fitness, same deltas. With an unchanged diagnosis, the cached LLM responses replay the same generation. It costs little budget, but it is a wasted generation that also blocks the 12 h slot. Now that ux-researcher is 0.922, the next generation should pick **devops-automator (0.805)**, so the loop breaks on its own.

### What broke
1. **Endpoint security alert (company PC, Trend Micro Apex One).** For item 4 the builder had no HTML validator. Youssef approved a local `npm install html-validate --ignore-scripts` into `…\02-evidence-collector\scratch\validator` (13 packages, about 10:41). Running its `.bin` shell shim through Git Bash failed to fork 5 times (`child_copy: stack write copy failed … Win32 error 5`). Apex One logged **5 "Program Library Injection" denials on `ZwWriteVirtualMemory`, Risk Low, Action Deny, last at 10:41**, from `…\AppData\Local\Programs\Git\usr\bin\sh.exe`. MSYS's fork copies memory into the child process, and behaviour monitoring read that as injection. Nothing ran that shouldn't have, but the network admin has to file a report. After that the session used **PowerShell only, with no downloads**, and every subagent handoff carried the same rule. No further alerts were reported.
2. **Judge miscount.** On the announcement task Qwen wrote "the third paragraph exceeds the 110-word limit (113 words)". It is 104 by whitespace split, alphanumeric regex and `[\w']+` (3 methods). The ensemble took that critique (correctness 0.75, top failure `word_count_violation`), and content-creator dropped from 0.965 to 0.915. Gemini gave 1.0; gpt-oss said "not independently verified" (0.7). LLM judges cannot count words. I changed nothing (judges are yours).
3. **Recorder call from PowerShell 5.1:** a `--feedback` string with embedded double quotes was split by PowerShell's native argument passing, and argparse rejected the call (nothing was recorded). The workaround was single quotes inside the text. This is not an engine bug, but the skill's examples assume a POSIX shell.
4. Gemini HTTP 503 on one judge call (transient). The task still has 2 judges, so it is not provisional.

### Changes / commits
- No code changes this session. Data commits by the cycle: `742d240` (scheduled 10:21), `de2364a` (manual 11:12). This STATUS: see `git log -1 -- docs/STATUS.md`.

### Answers to round 4's open questions
- Judge prompt size (from `llm_cache` usage since 3 Nov 13:45): gpt-oss median **3082** prompt tokens (max 5361, n=27); Qwen median **1820** (max 5716, n=22); Gemini median **2980** (max 6428, n=28).
- 22:17 skip message: confirmed on 3 Nov 22:17 and 4 Nov 10:17/16:17 and 5 Nov 04:17 (`evolve: skipped, last generation ran …h ago`). Generations ran at 4 Nov 04:22, 4 Nov 22:17 and 5 Nov 10:21.

### Open questions
1. **Deterministic length checks:** should the scorer count words, paragraphs and bytes itself when an acceptance criterion states a number (as it already does for output existence), so that a judge miscount cannot set the failure class?
2. **Replay guard for evolution:** skip a generation when target + diagnosis + persona hash equal the last generation's (or bypass the cache for proposals), so the 12 h slot is not spent on a replay.
3. **OpenRouter:** add Nemotron-3-ultra as a third lineage? If so, `EVOLVRA_MODEL_OPENROUTER` needs setting (the default id is gone), and Youssef should do that in `.env`.
4. **Leftover validator:** `~\.evolvra\missions\20261105-073059-build-a-single-file\02-evidence-collector\scratch\validator` (html-validate, 13 packages) is still on disk. Delete it, or keep it as mission evidence? I have not deleted anything.
5. **Machine constraint for future rounds:** this is a managed company PC. Any item that needs a download or install (validators, browsers, packages) should name a no-download alternative, or it will need an admin's OK.

**Still broken or unproven:** promotion on *real-mission* fitness is still unproven, because every real-data generation so far has been refused (correctly). Length/count criteria are judged by LLMs that cannot count. Evolution can replay a cached generation when the diagnosis does not change.
