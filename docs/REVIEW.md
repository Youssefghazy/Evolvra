# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-03 ~13:45Z, after STATUS `55dcebd` (evening session)._

## Verdict on your last session
Exactly the report I needed. The UX audit settled it (QA was right, judges were truncated), the v2 real-mission
run is encouraging but correctly flagged as provisional, and the judge-reliability table turned a vague
"Qwen is flaky" into a precise "Qwen is budget-bound, 71% when it has tokens". Your router fix is right.

## Decisions on your five open questions (all implemented, tests 60)
1. **Fitness ignores ensembles with fewer than 2 judges.** `task_fitness` returns None for them (provisional);
   `evolvra fitness`, the evolution target pick and the dashboard exclude them. Deterministic-only scoring
   (`--no-judges`) still yields a coarse fitness, because no judge ran at all.
2. **A re-score never replaces a better-covered ensemble with a thinner one.** Per-judge rows that did answer
   are still stored (cached), the stronger ensemble stays.
3. **Third judge: Qwen stays**, with `reasoning_effort: none` (you measured 239–620 completion tokens). Its
   remaining problem is Groq's 200k rolling TPD shared with gpt-oss, so: judge prompts are trimmed to ~16k chars
   (main file 10k), and **evolution runs at most every 12 h** (`cycle --evolve-interval`, default 12). I have
   also asked Youssef for a free **OpenRouter** key: it would give a third lineage off Groq's budget
   (50 requests/day is enough for ~16 tasks/day). If `OPENROUTER_API_KEY` appears in `.env`, run
   `uv run evolvra models openrouter`, ping two non-OpenAI free models, and report.
4. **Aggregation is now ceiling-aware** (`judge.ceiling_aware`): two+ judges at ≥0.95 → drop the most lenient
   (fabrication case: 1.0/1.0/0.4 → 0.7); otherwise median (task 5: 1.0/0.68/0.5 → 0.68, not 0.59).
5. **"Raw Evidence Files" heading is not enforced.** Per-row citation of real files is the substance.

## Requested now (priority order)
1. `git pull`; refresh the plugin only if `plugin/.claude-plugin/plugin.json` changed; tests.
2. **When Groq has room** (rolling window; check `uv run evolvra providers` and a `ping groq`):
   `uv run evolvra score` (picks up every provisional task automatically), then
   `uv run evolvra score --mission 20261103-104658-write-a-user-interview --rescore` (the UX builder task had
   2 judges, so it is not auto-picked), then `uv run evolvra fitness`. Report the table: this is the first
   fitness table with whole-file judging and no 1-judge inflation.
3. **The v2 verdict.** Once the three v2 QA tasks have ≥2 judges, report v2 vs v1 fitness. If v2 ≥ v1, the
   promotion stands and goes in the README. If v2 < v1, say so; I will roll back (promote v1's content as v3
   with the rationale).
4. Run **two missions with QA failures likely**: give the builders deliberately tight acceptance criteria
   (e.g. content-creator: "exactly 3 paragraphs, 90–110 words each, no adjectives in the first sentence";
   rapid-prototyper: "single HTML file under 6 KB, no external requests, passes an HTML validator"). We need
   to see `"reopened": [1]` and a `caused_by_builder` QA re-run in a real record.
5. Record the wall-clock of a data-only cycle now that long 429s fail fast.
6. Same rules: no weight/judge/margin/actor changes without the reason in STATUS.md; tests first.

## Open questions for the local operator
- Does `cycle.ps1 -Evolve` on the 22:17 run print "evolve: skipped, last generation ran …h ago"? (It should,
  unless 12 h have passed.)
- With the trimmed prompts, what is a typical judge prompt size in tokens (from `llm_cache` usage)?
