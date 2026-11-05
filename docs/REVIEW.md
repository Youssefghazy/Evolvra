# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-05 ~09:00Z, after STATUS `0c627ab` (round 5)._

## Verdict
Round 5 closed the proof. Verified against the export:
- **The promotion holds on real work:** Evidence Collector v2 0.924 over 7 real QA tasks vs v1 0.880 over 8,
  all with ≥2 judges. README updated.
- **The QA-retry path is on the record:** referral-loop mission, builder attempt 1 `FAIL` + `reopened_by_qa`,
  QA attempt 2 `PASS` + `caused_by_builder`, builder efficiency 0.5. Exactly as designed.
- UX Researcher 0.605 → 0.922 once judges saw the whole file.

Thank you for stopping at the security alert and switching to PowerShell-only. That was the right call.

## Decisions on your open questions (implemented, tests 62, plugin 0.3.2)
1. **Measured facts:** when a criterion mentions words/paragraphs/sentences/characters/lines/bytes, the judge
   prompt now carries program-computed counts of the main deliverable and an instruction to trust them.
2. **Replay guard:** same persona version + same diagnosis as the last generation → refused; `cycle` moves to the
   next weakest **current** version (old versions are no longer eligible targets).
3. **Third judge:** Nemotron-3-ultra (OpenRouter) replaces Qwen. Three seats on three providers. It is the
   OpenRouter default model in code, so `.env` needs no change. Qwen remains available via `EVOLVRA_JUDGES`.
4. **Leftover validator:** ask Youssef; if he agrees, delete only the `scratch\validator` folder (the QA report
   and raw evidence stay). Do not delete anything else.
5. **Machine constraint:** now in `CLAUDE.md` and the mission skill: no downloads or installs without Youssef's
   OK in-session; PowerShell, not Git Bash; single quotes for recorder text arguments.

## Requested now (short round)
1. `git pull`; refresh the plugin to 0.3.2 (`claude plugin marketplace update evolvra`,
   `claude plugin update evolvra@evolvra`); tests (expect 62).
2. `cd core; uv run evolvra score --rescore` once Groq has room. Report per-judge verdict counts: the point is to
   see Nemotron's reliability as a judge (verdicts vs errors, and whether its scores spread or sit at 1.0).
3. Re-score the announcement mission specifically and confirm the false "113 words" failure is gone:
   `uv run evolvra score --mission 20261105-072406-write-a-product-announcement --rescore`.
4. One mission for **devops-automator** (now the weakest): a PowerShell script with a `-WhatIf` mode and a
   self-test, no downloads. Then `.\scripts\cycle.ps1 -Evolve` when the 12 h slot allows.
5. Validator folder (decision 4). STATUS as usual.
