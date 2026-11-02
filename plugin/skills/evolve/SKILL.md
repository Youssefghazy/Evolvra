---
name: evolve
description: Evolve one Evolvra agent persona from its worst traces. Use when the user says "/evolvra:evolve <agent>", "improve this agent", or "why does <agent> keep failing". Phase 3 feature; in Phase 0 this skill runs the diagnosis step only.
---

# Evolvra Evolve

Target agent: `$ARGUMENTS` (a slug from `plugin/agents/MANIFEST.json`). If missing, list slugs and stop.

## Phase 0 behavior: diagnose only
1. Read the agent's current persona file in `plugin/agents/`.
2. Read its recent mission outputs under `${EVOLVRA_HOME:-~/.evolvra}/missions/*/<slug>/` and any FAIL
   verdicts aimed at it. If there are none, say so and stop; evolution needs evidence.
3. Produce a **failure taxonomy**: 2–5 named failure classes, each with the trace excerpt that proves it,
   and the persona section most likely responsible.
4. For each class, propose a *targeted* edit to the persona (which section, what to add or change, why).
   Do not rewrite the whole persona. Do not apply the edits yet.
5. Save the report to `${EVOLVRA_HOME:-~/.evolvra}/evolutions/<timestamp>-<slug>-diagnosis.md`.

## Later phases (not yet implemented, do not attempt)
Mutate into K=3 variants → lint → tournament on held-out task bank with free-tier judges → promote only if
the variant beats the parent → commit new version with rationale → update MANIFEST lineage.
