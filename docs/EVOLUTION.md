# Evolution (Phase 3)

`evolvra evolve <slug>` runs one generation of Darwinian improvement on a persona. Zero cost: every model
call goes to free tiers through the quota-guarded, cached router.

```
diagnose ──▶ mutate (K variants) ──▶ lint ──▶ proxy tournament ──▶ promote or archive
```

## 1. Diagnose
From scored missions: the agent's mean fitness, its failure classes (ensemble majority), and its worst
tasks with critiques, unmet acceptance criteria, QA feedback and an output excerpt. Written to
`~/.evolvra/evolutions/<ts>-<slug>/diagnosis.md`. With no scored tasks yet, evolution still runs on the
held-out bank alone.

## 2. Mutate
A mutator model (default Groq `openai/gpt-oss-120b`, override `EVOLVRA_MUTATOR=provider:model`) receives
the full persona and the diagnosis and writes **K full persona files, one targeted change each**, each
aimed at one failure class (real ones first, then generic ones such as `weak_evidence`). Frontmatter must
stay intact. Every candidate is linted with the agency-agents rules; failures are archived, never played.

## 3. Proxy tournament
Borrowed from GEPA/OpenEvolve: an **actor** model (default the same Groq model, `EVOLVRA_ACTOR`) plays each
persona as its system prompt on the agent's **held-out bank** (`plugin/agents/bank/<slug>.json` seeds plus
real mission tasks, deduplicated, newest missions first). The judge ensemble grades each deliverable.

Proxy fitness per task = 0.4 correctness + 0.2 completeness + 0.2 quality + 0.2 evidence; persona fitness =
mean over bank tasks. The actor is not Claude, so absolute numbers are a proxy; the *ranking* between parent
and variants is the signal.

## 4. Promote or archive
A candidate is promoted only if `fitness >= parent + margin` (default 0.03). Then:

- the persona file in `plugin/agents/` is overwritten with the winner,
- `MANIFEST.json` gets `version+1`, `parent`, and a history entry with the rationale,
- the registry records a new `agent_versions` row (`created_by = evolve`) linked to its parent,
- an `evolutions` row stores all candidates, the winner and the fitness delta.

Nothing is committed automatically. Review with `git diff plugin/agents` and commit; git history becomes the
evolution history. Losers stay on disk under the evolution directory with `report.md` and `result.json`.

## Budget
Calls per generation ≈ K + (1 + K_valid) × bank_size × (1 + judges). Defaults (K=3, bank 4, 3 judges)
≈ 3 + 4 × 4 × 4 = 67 calls, spread over Groq and Gemini. Well inside the daily caps; the cache makes reruns free.

## Commands
```bash
evolvra bank <slug>               # held-out tasks that will be used
evolvra evolve <slug> --dry-run   # targets + estimated calls, no network
evolvra evolve <slug>             # one generation
evolvra lineage <slug>            # version history with rationales
```
