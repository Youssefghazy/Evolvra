# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-05, after two days of unattended scheduled cycles (`8e7201d` … `6eb7d8f`). Supersedes round 4._

## What happened while nobody was watching
- The scheduler ran 6 cycles on its own, including 22:17 and 04:17: **the unattended loop is proven.**
- Every provisional verdict has been re-scored: **0 of 22 tasks provisional**, all with ≥2 judges.
- **v2 verdict:** Evidence Collector v2 0.886 (3 tasks) vs v1 0.880 (8 tasks), both with ≥2 judges. v2 ≥ v1, so
  **the promotion stands**. It is parity on real missions, not a big win; the README says so.
- Two ux-researcher generations ran and were refused (paired +0.01 and −0.004, margin 0.03). Correct refusals,
  but the target was chosen on a stale 0.605 that came from truncated judging.

## Finish line (priority order; this list completes the project)
1. `git pull`; refresh the plugin only if `plugin/.claude-plugin/plugin.json` changed; tests (expect 60).
2. **Fix the stale UX score:** `cd core; uv run evolvra score --mission 20261103-104658-write-a-user-interview --rescore`,
   then `uv run evolvra fitness`. Report before/after. (It had 2 judges under the old truncated input, so it is
   not auto-picked.)
3. **OpenRouter third judge (only if `OPENROUTER_API_KEY` is set in `.env`; never print it):**
   `uv run evolvra models openrouter`, then ping two free non-OpenAI models with `--model <id>`. Report ids,
   latency, `pong` or not. Do not change the judge set; I decide.
4. **Record a real QA-failure retry.** Run two missions with deliberately tight criteria:
   - `/evolvra:mission write a product announcement for a note app: exactly 3 paragraphs, each 90-110 words, the first sentence of each paragraph contains no adjectives, and it names exactly two features`
   - `/evolvra:mission build a single-file HTML pricing mock under 6 KB, zero external requests, three plan cards, and one keyboard-reachable toggle`
   If QA fails the builder, the record must show `"reopened": [1]` and a QA attempt with `caused_by_builder`.
   If both pass first time, say so; do not force a failure.
5. **Broaden the data:** two missions for agents with one task each: `growth-hacker` (a referral loop with a
   fraud-risk section) and `sprint-prioritizer` (rank 10 bugs by RICE with the formula shown).
6. `.\scripts\cycle.ps1 -Evolve` once (the 12 h interval may skip evolution; that is fine). Report the target,
   candidates, paired deltas and whether anything was promoted.
7. STATUS.md as usual, plus one line: anything you believe is still broken or unproven.

After this round the remaining work is presentation only (demo video, upstream contribution), owned by Youssef
and the reviewer.
