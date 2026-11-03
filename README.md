<p align="center">
  <h1 align="center">🧬 Evolvra</h1>
  <p align="center"><b>Survival of the promptest.</b></p>
  <p align="center">
    A self-evolving AI agency built on Claude Code. It runs a roster of specialist agents on real missions,
    scores every agent's work with evidence, and evolves the losers' personas, with a public dashboard
    that shows each agent's lineage, fitness curve, and the exact diff that made it better.
  </p>
</p>

<p align="center">
  <img alt="status" src="https://img.shields.io/badge/status-phase%203%20%C2%B7%20evolution-blue">
  <img alt="cost" src="https://img.shields.io/badge/total%20cost-%240.00-brightgreen">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-yellow">
  <img alt="runtime" src="https://img.shields.io/badge/runtime-Claude%20Code%20plugin-8A2BE2">
</p>

---

## What it does

1. **Mission.** `/evolvra:mission "Build a landing page for X"` runs the agency on a brief using the
   NEXUS protocol: phases, handoffs, Dev↔QA loops, quality gates. Every tool call and subagent result is traced.
2. **Score.** Each agent's output gets deterministic checks first (lint, tests, build), then a rubric judged by
   an ensemble of free-tier models, then a Reality Checker review only for borderline cases. Scores carry evidence.
3. **Evolve.** `/evolvra:evolve frontend-developer` reads the agent's worst traces, diagnoses failure classes,
   writes targeted persona variants, runs parent and variants on a held-out task bank, and promotes a variant
   **only if it beats its parent**. Losers go to a diversity archive. Winners get committed to git with a rationale.
4. **Show.** A static dashboard renders the roster, fitness over time, the genealogy tree of every agent,
   and side-by-side diffs between versions.

The moat is not any single prompt. It is the growing task bank, the eval traces, and a versioned
evolution history that nobody else can reproduce.

## Zero-cost by design

| Need | Choice | Cost |
|---|---|---|
| Creative + reflective work | Claude Code (your existing subscription) | $0 marginal |
| Bulk judging | Gemini Flash + Groq free tiers, OpenRouter free as fallback | $0 |
| Storage | SQLite + git | $0 |
| CI + hosting | GitHub Actions + GitHub Pages | $0 |

Hard rules: no payment card is ever attached to a provider, so a bug can throttle but never charge.
Keys live only in a gitignored `.env` or GitHub Secrets. A gitleaks hook blocks accidental commits.
The router counts daily requests per provider and stops *before* published limits.

## Architecture

```
Claude Code (plugin: plugin/)            core/ (Python, zero deps)              dashboard/ (static)
┌──────────────────────────┐   traces    ┌──────────────────────────┐  JSON    ┌────────────────────┐
│ agents/   10 → 280       │ ──────────▶ │ store/    SQLite schema  │ ───────▶ │ roster · fitness   │
│ skills/   mission evolve │             │ registry/ versions+lineage│          │ genealogy · diffs  │
│ hooks/    trace logger   │ ◀────────── │ router/   gemini|groq+cap│          │ GitHub Pages       │
└──────────────────────────┘  verdicts   │ evals/    (phase 2)      │          └────────────────────┘
                                         │ evolve/   (phase 3)      │
                                         └──────────────────────────┘
```

## Quick start (Phase 0)

```bash
# 1. Install the plugin into Claude Code
/plugin marketplace add Youssefghazy/Evolvra
/plugin install evolvra@evolvra

# 2. Set up the core
cd core && uv venv && uv pip install -e ".[dev]"
cp ../.env.example ../.env   # add your free-tier keys
evolvra init                 # creates ~/.evolvra/evolvra.db
evolvra import ../plugin/agents
evolvra agents               # lists the roster with versions
evolvra providers            # shows quota headroom per provider

# 3. After running /evolvra:mission in Claude Code
evolvra ingest               # load missions + traces into the DB
evolvra missions             # recent missions, tasks done, attempts
evolvra mission show <id>    # replay one mission: tasks, attempts, verdicts, trace counts
evolvra stats                # per-agent pass/fail
evolvra score                # deterministic checks + free-tier judge ensemble
evolvra fitness              # per agent version, weakest first: the evolution queue
evolvra evolve <slug>        # one generation: variants, tournament, promote only if it wins
evolvra lineage <slug>       # version history with rationales
```
Format details: [docs/MISSION-FORMAT.md](docs/MISSION-FORMAT.md).

## Roadmap

- [x] **Phase 0 — Skeleton.** Plugin scaffold, 10 starter agents, SQLite schema, provider router with quota guard, CI.
- [x] **Phase 1 — Missions.** Recorder-driven NEXUS runner with handoffs, 3-attempt Dev↔QA loop, gates; traces tagged per task; `evolvra ingest / missions / mission show / stats`.
- [x] **Phase 2 — Scoring.** Deterministic checks, 3-judge free-tier ensemble (Groq gpt-oss-120b, Gemini Flash-Lite, Gemma 4), per-task fitness, `evolvra score / fitness`. See [docs/SCORING.md](docs/SCORING.md).
- [x] **Phase 3 — Evolution.** Diagnose → mutate (K variants) → lint → proxy tournament on held-out banks → promote only if it beats the parent. `evolvra evolve`. See [docs/EVOLUTION.md](docs/EVOLUTION.md).
- [ ] **Phase 4 — Dashboard.** Roster, fitness curves, genealogy tree, diff viewer. Nightly export via Actions.
- [ ] **Phase 5 — Polish.** Inspect AI tasks, demo video, upstream PRs to agency-agents.

## Credits

Starter personas come from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT).
Evolution design borrows from [GEPA](https://github.com/gepa-ai/gepa), [OpenEvolve](https://github.com/codelion/openevolve)
and the [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954). See [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md).
Full research and plan: [docs/PLAN.md](docs/PLAN.md).

## License

MIT © 2026 Youssef Ghazy
