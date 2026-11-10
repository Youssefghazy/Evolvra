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
  <img alt="status" src="https://img.shields.io/badge/status-running%20autonomously-brightgreen">
  <img alt="tests" src="https://img.shields.io/badge/tests-60%20passing-brightgreen">
  <img alt="cost" src="https://img.shields.io/badge/total%20cost-%240.00-brightgreen">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-yellow">
  <img alt="runtime" src="https://img.shields.io/badge/runtime-Claude%20Code%20plugin-8A2BE2">
</p>

---

**Live dashboard:** https://youssefghazy.github.io/Evolvra/

## Results so far

Measured from the system's own records (`dashboard/public/data/`), first 9 days of operation.

| | |
|---|---|
| Real missions run | 23 (46 tasks, every one independently QA-checked) |
| QA rejections recorded and retried | 1 (builder reopened automatically; the retry is charged to the builder, not QA) |
| Evolution generations | 13 |
| Promotions | 2 (Evidence Collector v1 → v2; DevOps Automator v1 → v2), both confirmed on real missions |
| Generations correctly refused | 11 (no candidate beat its parent by the margin, or the arena was unfair) |
| Free-tier model calls | ~560 (Gemini, Groq, OpenRouter) |
| Money spent | **$0.00** |
| Scheduled cycles that ran unattended | 20+, including a whole weekend |

**The promotion.** The judges kept flagging Evidence Collector, the QA agent, for claims it could not prove.
Evolution read those failures, wrote three persona variants, and played each against the original on four
held-out tasks. The winner added one workflow step ("save every command's raw output under `evidence/`"), a
report section listing those files, and an automatic-fail rule for any claim without a referenced file.

| | v1 (original) | v2 (evolved) |
|---|---|---|
| Arena, 4 held-out tasks (paired) | 0.63 | **0.80** (+0.17) |
| Real missions, ≥2 judges | 0.880 (8 tasks) | **0.924** (7 tasks) |

The arena predicted the improvement, and it then held on work the arena never saw: across seven real QA tasks
after promotion, v2 scored higher than v1 did across its eight. Every v2 report saved real raw command output
under `evidence/` and cited it per finding, which is exactly the behaviour the promotion targeted.

**The second promotion.** DevOps Automator v2 beat v1 by +5.75 points in the arena (generation 12, the first
in which all three rewrites played, two of them written by the Gemini fallback for large personas). On real work:

| | v1 (original) | v2 (evolved) |
|---|---|---|
| Real missions, ≥2 judges | 0.881 (4 tasks, min 0.72) | **0.973** (3 tasks, min 0.96) |

The v2 tasks were different kinds of work (a CI workflow with its checker, a backup verifier, a log parser), so this
is consistent with the arena result rather than a like-for-like proof, and it is stated that way.

**What three days of running taught the engine.** Each of these was found by the system's own operator
session, fixed test-first, and is now enforced in code:
judges were reading only the first 4,000 characters of long deliverables; two lenient judges could outvote the
one that caught fabricated evidence (aggregation is now ceiling-aware); a single wrong low judge could sink
correct work (median when judges genuinely disagree); a rate-limited day could overwrite a 3-judge verdict with
a 1-judge one; QA retries caused by a builder were charged to QA; a promoted persona was not shipped to the
installed plugin; LLM judges miscounted words (counts are now measured by code and given to them); and an
unchanged generation could replay from cache (now refused, the next weakest agent goes instead). Details: [docs/SCORING.md](docs/SCORING.md), [docs/EVOLUTION.md](docs/EVOLUTION.md).

## How it runs: two Claude sessions and a timer

- **Operator** (local Claude Code, on the owner's Pro plan): runs missions, cycles and audits, fixes engine
  bugs test-first, and writes [`docs/STATUS.md`](docs/STATUS.md).
- **Reviewer** (cloud Claude session): reads STATUS from git, reviews every commit, owns scoring and evolution
  policy, and writes [`docs/REVIEW.md`](docs/REVIEW.md).
- **Scheduler** (Windows Task Scheduler): every 6 hours ingests, scores, evolves the weakest agent at most every
  12 hours, exports and pushes. The dashboard redeploys on every push.

Git is the only channel between them, so every decision has a commit and a reason.

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

## Quick start

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
evolvra export               # JSON snapshots for the dashboard (then commit + push to publish)
evolvra cycle [--evolve]     # ingest -> score -> [evolve weakest] -> export -> commit -> push, in one go
```
Windows users: `scripts\schedule.ps1` runs the cycle on a timer, so missions you run get scored, evolved
and published without touching a terminal.

Format details: [docs/MISSION-FORMAT.md](docs/MISSION-FORMAT.md).

## Roadmap

- [x] **Phase 0 — Skeleton.** Plugin scaffold, 10 starter agents, SQLite schema, provider router with quota guard, CI.
- [x] **Phase 1 — Missions.** Recorder-driven NEXUS runner with handoffs, 3-attempt Dev↔QA loop, gates; traces tagged per task; `evolvra ingest / missions / mission show / stats`.
- [x] **Phase 2 — Scoring.** Deterministic checks, 3-judge free-tier ensemble from three lineages (Groq gpt-oss-120b, Groq Qwen 3.8, Gemini Flash-Lite), ceiling-aware aggregation, provisional verdicts below 2 judges, `evolvra score / fitness`. See [docs/SCORING.md](docs/SCORING.md).
- [x] **Phase 3 — Evolution.** Diagnose → mutate (K variants) → lint → proxy tournament on held-out banks → promote only if it beats the parent. `evolvra evolve`. See [docs/EVOLUTION.md](docs/EVOLUTION.md).
- [x] **Phase 4 — Dashboard.** Static Vite + React site on GitHub Pages: overview, roster, genealogy, fitness by version, version diffs, missions with per-judge scores, evolutions. `evolvra export`. See [docs/DASHBOARD.md](docs/DASHBOARD.md).
- [x] **Phase 4b — Autonomy.** `evolvra cycle`, Windows scheduler, operator/reviewer protocol over git (`CLAUDE.md`, STATUS/REVIEW).
- [ ] **Phase 5 — Proof and polish.** ~~A second promotion on another agent~~ (DevOps Automator v2, 8 Nov, confirmed on 3 real tasks), ~~a recorded QA-failure retry~~, demo video, upstream contribution to agency-agents.

## Credits

Starter personas come from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT).
Evolution design borrows from [GEPA](https://github.com/gepa-ai/gepa), [OpenEvolve](https://github.com/codelion/openevolve)
and the [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954). See [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md).
Full research and plan: [docs/PLAN.md](docs/PLAN.md).

## License

MIT © 2026 Youssef Ghazy
