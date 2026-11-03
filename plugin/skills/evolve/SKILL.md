---
name: evolve
description: Evolve one Evolvra agent persona from evidence. Use when the user says "/evolvra:evolve <agent>", "improve this agent", or "why does <agent> keep failing".
---

# Evolvra Evolve

Target agent: `$ARGUMENTS` (a slug from `${CLAUDE_PLUGIN_ROOT}/agents/MANIFEST.json`). If missing, run
`evolvra fitness` (or list the slugs) and ask which agent to evolve, then stop.

## Preferred path: the core engine (zero-cost, automatic)
Run from the repo's `core/` directory (use `uv run evolvra ...` or `.venv\Scripts\evolvra ...`):

```
evolvra ingest
evolvra score
evolvra evolve <slug> --dry-run     # shows targets, bank size, estimated free-tier calls
evolvra evolve <slug>               # diagnose -> 3 variants -> proxy tournament -> promote only if it wins
```

Then read the printed `report.md`, and show the user:
1. Parent fitness vs each candidate, and whether a promotion happened.
2. If promoted: `git diff plugin/agents/<file>.md` summarized in 3 bullets (what rule changed and why).
3. Offer to commit with message `evolve(<slug>): v<N> <target>`; commit only if the user says yes.

## Fallback: diagnose manually (when the CLI is unavailable)
1. Read the persona in `${CLAUDE_PLUGIN_ROOT}/agents/`.
2. Read its mission outputs under `${EVOLVRA_HOME:-~/.evolvra}/missions/*/NN-<slug>/` and FAIL feedback.
3. Write a failure taxonomy (2–5 classes with the trace that proves each) and ONE targeted persona edit per
   class, to `${EVOLVRA_HOME:-~/.evolvra}/evolutions/<timestamp>-<slug>-diagnosis.md`. Do not apply edits.

## Rules
- Never promote a variant without a tournament result that beats the parent. Evidence over taste.
- Never rewrite a persona wholesale. One targeted change per variant.
- Evolved files must stay valid agency-agents personas (frontmatter name/description/color intact).
