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
| OpenRouter · `nvidia/nemotron-3-ultra-550b-a55b:free` | different lineage (NVIDIA), different provider budget |
| Gemini · `gemini-3.5-flash-lite` | fast, generous free quota; lenient |

History: Gemma 4 dropped 2026-11-03 (failed most calls, 1.0 on the rest). Qwen 3.8 (Groq) replaced 2026-11-05: it
shared Groq's 200k tokens/day with gpt-oss and starved on busy days. Three providers now carry the three seats.

**Measured facts.** When an acceptance criterion mentions words, paragraphs, sentences, characters, lines or
bytes, the judge prompt carries program-computed counts of the main deliverable (bytes, words, prose paragraphs,
words per paragraph) and an instruction to trust them over its own counting. LLM judges miscount: on 2026-11-05 a
judge called a 104-word paragraph 113 words and set the failure class.

**Criteria by id, read literally.** The prompt numbers the acceptance criteria (`C1. ...`) and judges answer
per id, with an instruction not to restate, merge, split or narrow a criterion. Answers are mapped back to the
criteria as written; an entry that matches none is kept but marked `rewritten` and left out of the evolution
diagnosis. On 2026-11-05 a judge narrowed "the text names exactly two product features" to "each paragraph
names…", failed it, and that misread became content-creator's top failure class.

**Lone dissent is labelled, not dropped.** When the failure class comes from a single judge, no other judge
raised any failure, and at least two others put correctness at the ceiling, the ensemble keeps the class but
records `contested_by`. The score is unchanged (the ceiling rule still applies). It is labelled rather than
discarded because the same shape caught fabricated evidence on 2026-11-03. Contested classes are shown as
`(contested)` in `evolvra fitness`, lose ties to uncontested ones, are not counted when the diagnosis ranks
which failures the rewrites should target, and appear in the diagnosis with the per-criterion vote
("unmet per X; 2 other judges marked it met") so the coach can check them against the output.

**What the judge is shown.** Up to 16,000 characters of the output folder (headers included), each file labelled
with its path. Every file is ranked on metadata before anything is cut, so thousands of fixtures cannot hide the
report; folders of scratch, copies or more than 50 unrecognised files go last and are summarised as one line.
Proof files that the main report cites by path come before other proof files.
Order: the main deliverable (the largest non-scratch file the agent mentions), then proof files (`evidence/`,
`results/`, `logs/`… or anything mentioned by path), then other named files, then the rest, with `scratch/`,
`work/` and `fixtures/` last. When proof files exist, the main file is capped at ~35% of the budget and the proof
files share most of the rest; a file that does not fit whole still gets an excerpt; files left out are named with a
note that they exist. Empty files are skipped. On 8 Nov a long QA report had pushed 73 of 75 proof files out.

Override with `EVOLVRA_JUDGES="groq:openai/gpt-oss-120b,gemini:gemma-4-31b-it"` or `evolvra score --judges ...`.

Each judge sees the brief, the agent's role, the task, the acceptance criteria, the agent's evidence
statement, and the output files (text, truncated). It must answer with strict JSON:

```json
{"acceptance": [{"id": "C1", "met": true, "reason": "..."}],
 "correctness": 0.8, "completeness": 0.9, "quality": 0.7, "evidence": 0.8,
 "critique": "one sentence", "failure_class": "snake_case_or_none"}
```

Every judge's row is stored (`judge_model = provider/model`). The **ensemble** row is **ceiling-aware**:
with three or more valid judges, if two or more scores sit at the ceiling (≥ 0.95) the most lenient one is
dropped and the rest averaged (lenient judges park at 1.0; this is the fabricated-evidence case,
1.0/1.0/0.4 → 0.7); otherwise the judges genuinely disagree and the median is used, so one factually wrong
low judge cannot sink correct work (1.0/0.68/0.5 → 0.68). With two judges it is the plain mean.
A verdict backed by fewer than 2 judges is **provisional**: it does not count toward fitness, the task is
picked up again by the next `evolvra score`, and a re-score never replaces a better-covered ensemble with
a thinner one. The `failure_class` and critique come from the strictest
judge that found a problem (ties broken by majority), because the diagnosis exists to surface problems.
The judge prompt carries calibration anchors: 1.0 is reserved for flawless and verifiable work; invented
measurements cap evidence at 0.2 and correctness at 0.5. Judges that error or return unparseable output are
recorded as `rubric:error` and excluded (also when the coverage guard keeps an older ensemble, so the cause of
every missing verdict stays on record); one valid judge is enough to produce an ensemble. Judges get 900 output
tokens and one retry at 2400 if cut off; Nemotron gets 2400 first, because OpenRouter's free tier counts
requests (40/day), not tokens, and the retry was costing it a second request on many verdicts.

Calls go through the router: daily caps stop before free limits, and identical prompts hit the SQLite
cache, so `evolvra score --rescore` costs zero requests **while the prompt is unchanged**. Any change to the
judge prompt (such as numbering the criteria) makes every rescore a fresh call. When only the aggregation
rule changes, use `evolvra reaggregate`: it rebuilds every ensemble from the stored judge rows with no calls.

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

Missing components are dropped and the rest renormalized, so deterministic-only scoring (`--no-judges`)
still yields a coarser fitness. A task whose judges ran but fewer than 2 answered has no fitness until it
is re-scored. `evolvra fitness` lists agents weakest first with their top failure class: the
input queue for `/evolvra:evolve`.

## Commands

```bash
evolvra ingest                 # load missions + traces
evolvra score --dry-run        # what would be scored, with which judges
evolvra score                  # checks + ensemble on every unscored finished task
evolvra score --no-judges      # deterministic only, no network
evolvra score --mission <id>   # one mission
evolvra score --rescore        # recompute (served from cache only if the prompt is unchanged)
evolvra reaggregate            # re-apply aggregation rules to stored verdicts, 0 API calls
evolvra fitness                # per agent version, weakest first
```
