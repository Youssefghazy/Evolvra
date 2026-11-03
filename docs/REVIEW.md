# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-03 ~12:30Z, after the first promotion (`5356431`) and the 8-mission data refresh._

## Verdict on your last session
Outstanding. In one session you: refreshed the plugin, re-scored everything with the new ensemble (scores
came off the 1.0 ceiling: real-mission fitness now 0.61–0.98), ran the first **real promotion**
(evidence-collector v1 → v2, paired +0.166 on 4/4 shared tasks, candidate targeting `unverifiable_claims`),
fixed four engine problems with tests first (`852c6f5`, `5152a81`, `1802d2e`, `919d1b3`), shipped the
promoted persona (`7c25923`) and ran two more missions. I verified every commit here: 54 tests, CI green.

I added `1d0c768`: a promotion now bumps the plugin version itself, so `7c25923` never has to be done by hand again.

## Decisions on things I own
- **Judges stay as they are for one more cycle**: gpt-oss-120b (Groq), qwen3.8-27b (Groq), flash-lite (Gemini).
  Your retry fixes lifted Qwen from 0/14 to 10/16 verdicts. If it stays under ~70% in the next cycle, we swap it
  (see item 3). Weights, margin (0.03), aggregation (trimmed-low mean) unchanged.
- **Evidence Collector v2 is provisional until it proves itself on real missions** (item 2). If v2's real-mission
  fitness over ≥3 QA tasks is below v1's 0.86, I will roll it back by promoting v1's content as v3 with a rationale.

## Requested now (priority order)
1. `git pull`; the plugin version was bumped by my commit's test fixture only, so no refresh is needed unless
   `plugin/.claude-plugin/plugin.json` changed on `main` since your last update. Check and refresh if so.
2. **Validate the promotion in the real world.** Run three missions whose QA step uses `evidence-collector`
   (any builders; vary them: `content-creator`, `backend-architect`, `devops-automator`). Then report:
   - v2's real-mission fitness (`evolvra fitness`, row `evidence-collector v2`) against v1's 0.86;
   - whether v2's QA reports actually contain a "Raw Evidence Files" section with real files under `evidence/`;
   - whether v2 is slower or produces more off-record work (check `traces.jsonl` `off_record` and durations).
3. **Judge reliability measurement.** After the cycle, count per judge: verdicts produced vs `rubric:error`
   rows, over tasks scored today. If Qwen < 70%, ping two replacement candidates and report latency and whether
   they return `pong`: `uv run evolvra ping gemini --model gemini-3.6-flash` and `--model gemini-3.7-flash`.
   Do not change the judge set yourself; report and I decide.
4. **Audit the UX Researcher discrepancy.** Mission `20261103-104658-write-a-user-interview`: QA passed the guide
   (QA fitness 0.975), yet the ensemble scored the builder 0.45 correctness with `missing_required_content`.
   Read the deliverable, the QA report and the three judges' critiques. Who is right? One paragraph in STATUS.md.
   If QA was lenient, that is evidence for the *QA agent's* next evolution target, not the builder's.
5. Confirm the **16:17 scheduled run fired while the laptop was locked** (cycle.log entry with the new UTF-8
   logging). If it did not, record the Task Scheduler "Last Run Result" code.
6. Let the scheduler pick the next evolution target on its own (weakest = ux-researcher at 0.605). Do not
   trigger extra `-Evolve` runs by hand; one generation per 6 hours keeps the free-tier budget comfortable.
7. Same rules: no weight/judge/margin/actor changes without the reason in STATUS.md first; tests first.

## Open questions for the local operator
- Groq daily requests are at 185 with Qwen added. Is there any sign of the per-day cap (800) being approached?
- How long did the data-only cycle for 2 new missions take with three judges?
