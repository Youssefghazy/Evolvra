# Scoring (Phase 2)

Every finished task gets scored in three layers, cheapest first. All of it is free.

## 1. Deterministic checks (instant, no network)

| Metric | 1.0 when |
|---|---|
| `det:output_exists` | the task's `output_dir` contains at least one file |
| `det:evidence_present` | the final attempt carries an `evidence` statement of 10+ characters |
| `det:efficiency` | `1 / attempts`, not counting QA re-runs forced by a builder fix (first-try pass = 1.0, third try = 0.33) |
| `det:verdict` | the orchestrator's recorded verdict is `PASS` |

## 2. Judge ensemble (free tiers, cached)

Three judges from three training lineages, so no single vendor's taste dominates:

| Judge | Why |
|---|---|
| Groq · `openai/gpt-oss-120b` | strong reasoning; the strictest judge in practice |
| Groq · `qwen/qwen3.8-27b` | different lineage (Alibaba), fast |
| Gemini · `gemini-3.5-flash-lite` | fast, generous free quota; lenient |

Gemma 4 was dropped on 2026-11-03: it failed most calls and gave 1.0 to everything it did answer.

Override with `EVOLVRA_JUDGES="groq:openai/gpt-oss-120b,gemini:gemma-4-31b-it"` or `evolvra score --judges ...`.

Each judge sees the brief, the agent's role, the task, the acceptance criteria, the agent's evidence
statement, and the output files (text, truncated). It must answer with strict JSON:

```json
{"acceptance": [{"criterion": "...", "met": true, "reason": "..."}],
 "correctness": 0.8, "completeness": 0.9, "quality": 0.7, "evidence": 0.8,
 "critique": "one sentence", "failure_class": "snake_case_or_none"}
```

Every judge's row is stored (`judge_model = provider/model`). The **ensemble** row is the **trimmed-low
mean**: with three or more valid judges the single most lenient score per metric is dropped and the rest
averaged; with two it is the plain mean. The median was replaced on 2026-11-03 after two lenient judges
outvoted the one that caught fabricated evidence. The `failure_class` and critique come from the strictest
judge that found a problem (ties broken by majority), because the diagnosis exists to surface problems.
The judge prompt carries calibration anchors: 1.0 is reserved for flawless and verifiable work; invented
measurements cap evidence at 0.2 and correctness at 0.5. Judges that error or return unparseable output are
recorded as `rubric:error` and excluded; one valid judge is enough to produce an ensemble.

Calls go through the router: daily caps stop before free limits, and identical prompts hit the SQLite
cache, so `evolvra score --rescore` costs zero requests.

## 3. Fitness

One number per task, rolled up per **agent version**. This is what evolution optimizes.

| Component | Weight |
|---|---|
| `rubric:correctness` | 0.35 |
| `rubric:completeness` | 0.15 |
| `rubric:quality` | 0.15 |
| `rubric:evidence` | 0.10 |
| `det:verdict` | 0.10 |
| `det:efficiency` | 0.10 |
| `det:output_exists` | 0.05 |

Missing components are dropped and the rest renormalized, so deterministic-only scoring still yields a
(coarser) fitness. `evolvra fitness` lists agents weakest first with their top failure class: the
input queue for `/evolvra:evolve`.

## Commands

```bash
evolvra ingest                 # load missions + traces
evolvra score --dry-run        # what would be scored, with which judges
evolvra score                  # checks + ensemble on every unscored finished task
evolvra score --no-judges      # deterministic only, no network
evolvra score --mission <id>   # one mission
evolvra score --rescore        # recompute (served from cache)
evolvra fitness                # per agent version, weakest first
```
