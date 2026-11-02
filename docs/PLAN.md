# Self-Evolving Agency — Research & Build Plan

> A portfolio-grade, zero-cost system that turns the 280-agent `agency-agents` roster into
> an AI company that measurably improves its own agents after every mission.

Status: research complete, build not started. Date: 2026-11-02.

---

## 0. The constraints that shape everything

| Constraint | Consequence |
|---|---|
| Solo builder | Agents do the heavy lifting. Architecture must be simple enough for one person to hold in their head. |
| Zero money spent | No paid APIs, no paid hosting, no paid DBs. Only free tiers, local models, and the Claude subscription you already have. |
| Portfolio | The demo must be visual and self-explanatory. The "agents evolving" story must be visible in 30 seconds. |
| Unique / hard to copy | The moat is the evolution loop + accumulated eval data + versioned persona genealogy, not any single prompt. |

**Assumption:** you already pay for a Claude plan (you are using Claude Code now). Using it for your own
personal tooling is ordinary use, so marginal cost is zero. Anthropic's terms say products built for *other
users* on the Agent SDK must use API keys, so the design keeps Claude Code as *your* runtime and never
routes other people's requests through your seat.

---

## 1. What exists today (research findings)

### 1.1 The base roster: `msitarzewski/agency-agents`
- ~280 persona files in 18 divisions, MIT. Each has YAML frontmatter (`name`, `description`, `color`, `emoji`, `vibe`) and a long system prompt.
- Already contains **NEXUS**, a documented orchestration protocol in `strategy/`: 7 phases (Discovery → Operate), handoff templates, Dev↔QA loop with "max 3 retries then escalate", quality gates, "evidence over claims".
- Has QA personas we can repurpose as evaluators: Reality Checker, Evidence Collector, API Tester, Performance Benchmarker, UI Finish Gate Reviewer.
- Has `scripts/lint-agents.sh` (frontmatter validation) and `scripts/convert.sh` (renders agents for 17 tools). Our evolved personas must stay lint-clean so they remain installable anywhere.
- Gap we fill: NEXUS is **static text**. Nothing scores agents, nothing learns, nothing changes the persona files. That is exactly our product.

### 1.2 Self-improving-agent research (what "evolution" should mean)
| Project | Idea we borrow | License |
|---|---|---|
| **GEPA** (gepa-ai/gepa, 7k★, `dspy.GEPA`) | *Reflective* mutation: an LLM reads full execution traces, diagnoses failures, proposes a targeted edit. Pareto front of candidates, not a single score. Provider-agnostic. | MIT |
| **OpenEvolve** (codelion/openevolve, 7.7k★) | MAP-Elites archive keeps *diverse* champions; island populations with migration; evaluator "artifacts" (errors) fed back into the next mutation prompt; everything seeded. Has a prompt-optimization example. Supports OpenAI-compatible APIs **and the Claude Code CLI as a model backend**. | Apache-2.0 |
| **Darwin Gödel Machine** (jennyzzt/dgm, ICLR 2026) | Archive of agent variants; each self-modification is accepted only if it empirically scores higher. Research code, expensive, needs Docker + paid APIs. We copy the *principle*, not the code. | Apache-2.0 |
| **DSPy** | Programmatic prompts + optimizers; GEPA lives here. Good for the evaluator layer. | MIT |

Design takeaway: **GEPA-style reflection + MAP-Elites archive + DGM-style "only promote if it wins"**,
applied to persona Markdown files, versioned in git.

### 1.3 Orchestration frameworks
- **LangGraph**: most control, Python, stateful graphs. **CrewAI**: fastest role-based teams. **Mastra**: best TypeScript. **Pydantic AI**: typed single agents. **AG2**: research.
- **Decision:** do not adopt a heavy framework for v1. Claude Code *is* the orchestrator (subagents, skills, hooks, plugins). A thin Python package handles scoring + evolution. Keep an adapter so the same personas can later run under LangGraph/CrewAI for a "run anywhere" demo.

### 1.4 Evals
- **Inspect AI** (UK AISI, MIT): strongest for agent/tool-use evals, Python. **promptfoo**: YAML, CI gating, LLM-as-judge (reportedly acquired by OpenAI, Mar 2026; still open source). **DeepEval**: pytest-style.
- **Decision:** own lightweight rubric + deterministic checks first (fast, free). Add Inspect AI tasks in Phase 4 for credibility.

### 1.5 Memory / observability
- **Mem0** (Apache-2.0, lightest to self-host, embedded store). **Letta** (full runtime, heavier). Zep community edition deprecated.
- **Langfuse** core MIT, self-hostable; **Arize Phoenix** Elastic-2.0, free self-host, OpenTelemetry-native.
- **Decision:** SQLite as the system of record (zero infra). Optional Phoenix locally when you want pretty traces.

### 1.6 Free compute (verified Nov 2026, numbers are third-party, re-check on signup)
| Provider | Free tier (approx.) | Role in our stack |
|---|---|---|
| **Claude Code** (your subscription) | Your plan's usage | Primary runtime for missions + evolution reflection (highest quality). |
| **Google Gemini 2.5 Flash / Flash-Lite** | ~15 RPM, ~1,500 RPD, 1M TPM, no card. Prompts may be used for training. | Bulk evaluation runs, cheap judge model. |
| **Groq** (llama-3.3-70b, gpt-oss-120b) | ~30 RPM, ~1,000 RPD, 12K TPM, per-org. | Fast judge / secondary evaluator for ensemble scoring. |
| **OpenRouter `:free` models** | 50 RPD without credits. | Fallback only. |
| **Ollama** (local: Qwen3 8B class) | Unlimited, needs ~8–16 GB RAM. | Offline/unlimited judge if your machine allows. |
| ~~GitHub Models~~ | **Retired July 30, 2026.** | Do not plan on it. |
| Cerebras | Trial credits, card required. | Skip. |

Rule: **evaluator calls go to free providers; creative/reflective calls go to Claude Code.** Rate-limit-aware router with backoff; everything cached in SQLite so a rerun costs nothing.

### 1.7 Free hosting / infra
- **GitHub**: repo, Actions (free for public repos), **Pages** for the dashboard, Releases for exports. This is the backbone.
- **Vercel Hobby** (non-commercial) or **Cloudflare Pages/Workers Free** (100k req/day) if we want a serverless API later.
- **Supabase Free** (500 MB Postgres, pauses after ~1 week idle) only if we need multi-device sync. Default: no.
- **Render Free** spins down after 15 min; avoid for anything interactive.

### 1.8 UI
- **CopilotKit + AG-UI** (MIT, 30k★) if we want a live chat-with-the-agency panel.
- Dashboard: **Vite + React + Tailwind + shadcn/ui**, static export to GitHub Pages, reading JSON snapshots exported from SQLite. Zero backend.

---

## 2. Product definition

**One sentence:** *A Claude Code plugin that runs the Agency as a company on any brief, scores every agent's
work with evidence, and evolves the losing agents' personas overnight, with a public dashboard that shows
each agent's lineage, fitness curve, and the exact diff that made it better.*

**The 30-second demo:**
1. `/agency:mission "Build a landing page for X"` → NEXUS-Sprint runs with 6 agents, you watch handoffs.
2. Dashboard shows each agent's score on that mission, with evidence (tests passed, rubric hits, reviewer verdict).
3. `/agency:evolve frontend-developer` → engine reflects on the three worst traces, proposes 3 persona variants, runs them on the task bank, promotes the winner.
4. Dashboard shows the **genealogy tree**: v1 → v2 → v3 with fitness going 0.61 → 0.68 → 0.74, and a readable diff of what changed ("added explicit a11y checklist step").

### What makes it hard to copy
- The **task bank + eval traces** grow every run. Six months in, nobody can reproduce your fitness history.
- Evolution is **reflective and evidence-grounded**, not random prompt shuffling.
- Output stays **portable**: evolved personas remain valid agency-agents files, installable into Cursor, Codex, Gemini CLI via the upstream scripts. You could upstream improvements as PRs — a visible portfolio signal.

---

## 3. Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│  Claude Code (your subscription)                                      │
│  plugin: agency-evolve/                                               │
│   ├─ agents/        ← active roster (symlinked/synced from registry)  │
│   ├─ skills/        /agency:mission  /agency:evolve  /agency:report   │
│   ├─ hooks/         PostToolUse + SubagentStop → append trace to DB   │
│   └─ .mcp.json      local "agency-db" MCP server (read/write SQLite)  │
└───────────────┬───────────────────────────────────────────────────────┘
                │ traces, artifacts, verdicts
┌───────────────▼───────────────────────────────────────────────────────┐
│  core/ (Python, uv)                                                   │
│   registry/   persona files + versions + lineage (git-backed)         │
│   missions/   NEXUS runner: phases, handoffs, retries, gates          │
│   evals/      deterministic checks + rubric judge + reviewer agents   │
│   evolve/     reflect → mutate → tournament → promote (GEPA + MAP-E)  │
│   router/     LiteLLM: claude-code | gemini | groq | ollama + cache   │
│   store/      SQLite: runs, traces, scores, variants, lineage         │
└───────────────┬───────────────────────────────────────────────────────┘
                │ export JSON snapshots (GitHub Action, nightly)
┌───────────────▼───────────────────────────────────────────────────────┐
│  dashboard/ (Vite + React + shadcn, static → GitHub Pages)            │
│   Roster · Mission replay · Fitness curves · Genealogy tree · Diffs   │
└───────────────────────────────────────────────────────────────────────┘
```

### Data model (SQLite)
- `agents(id, slug, division, current_version)`
- `agent_versions(id, agent_id, version, content_md, parent_version, created_by, rationale)`
- `missions(id, brief, mode, started_at, status)`
- `tasks(id, mission_id, agent_version_id, input, output, attempt)`
- `traces(id, task_id, tool, args_json, result_json, ts)`
- `scores(id, task_id, metric, value, evidence_json, judge_model)`
- `evolutions(id, agent_id, parent_version, candidate_versions_json, winner_version, bank_delta)`

### Evolution loop (per agent)
1. **Select**: agents whose rolling fitness < division median, or user-chosen.
2. **Diagnose** (Claude Code): read the N worst traces; produce a structured failure taxonomy.
3. **Mutate**: produce K=3 persona variants, each targeting one failure class; must pass `lint-agents.sh`.
4. **Tournament**: parent + variants run the agent's **task bank** (held-out tasks). Judges on free providers, deterministic checks first.
5. **Promote** only if a variant beats parent on the held-out bank by a margin (anti-regression), else archive it in the MAP-Elites grid by (style axis, length axis) for diversity.
6. **Commit**: new version file + CHANGELOG line + lineage row. Git history *is* the evolution history.

### Scoring (cheap first, smart last)
1. Deterministic: lint, tests pass, build succeeds, required sections present, link/URL validity.
2. Rubric judge (free model ensemble, Gemini + Groq, majority vote).
3. Reviewer persona (Reality Checker / Evidence Collector via Claude Code) only for borderline cases.

---

## 4. Build phases (solo, zero cost)

| Phase | Goal | Deliverable | Est. |
|---|---|---|---|
| **0. Skeleton** | Repo, plugin manifest, SQLite schema, import roster | `/agency:mission` runs one agent and logs a trace | 1 week |
| **1. Missions** | NEXUS-Micro and Sprint runner with handoffs, retries, gates | Replayable mission log | 1–2 weeks |
| **2. Scoring** | Deterministic checks + free-provider rubric judge + cache | Every task has a score with evidence | 1 week |
| **3. Evolution** | Reflect → mutate → tournament → promote; task bank seeded with 10 tasks/agent for 10 starter agents | First promoted v2 with a real diff | 2 weeks |
| **4. Dashboard** | Static site: roster, fitness curves, genealogy tree, diff viewer; nightly Action export | Public GitHub Pages URL | 1–2 weeks |
| **5. Polish** | Inspect AI tasks, README with GIFs, demo video, optional upstream PRs | Portfolio-ready | 1 week |

Start small: **10 agents** (Frontend Dev, Backend Architect, Rapid Prototyper, UX Researcher, Reality
Checker, Evidence Collector, Content Creator, Growth Hacker, Sprint Prioritizer, DevOps Automator).
Add divisions once the loop is proven.

---

## 5. Stack decisions (final)

| Layer | Choice | Why free | Why this |
|---|---|---|---|
| Runtime | Claude Code plugin | Existing subscription | Best model, native subagents/hooks, zero infra |
| Core | Python 3.12 + `uv`, `litellm`, `sqlite3`, `pydantic` | OSS | One language for evals + evolution |
| Judges | Gemini Flash + Groq (ensemble), Ollama optional | Free tiers | Diversity reduces judge bias |
| Evolution | Own implementation inspired by GEPA/OpenEvolve; optional `dspy.GEPA` for the rubric prompts | MIT/Apache | Full control, small codebase |
| Evals | Own rubric + Inspect AI (Phase 5) | MIT | Credibility |
| Store | SQLite + git | Free | Portable, diffable, zero ops |
| Dashboard | Vite + React + Tailwind + shadcn/ui, GitHub Pages | Free | Beautiful, static, no backend |
| CI | GitHub Actions (public repo) | Free | Nightly export + lint |

---

## 6. Names (pick one)
- **Darwin Agency** · **Evolvra** · **NEXUS Evolve** · **Genome** · **Lineage** · **The Living Agency**

## 7. Open questions for you
1. Project name?
2. Your machine RAM / GPU (decides whether Ollama is a judge option)?
3. GitHub username so we create the public repo (needed: this cloud container is wiped between sessions).
4. Public repo from day one (free Actions + Pages) or private until the demo works?

## 8. Sources
- agency-agents: https://github.com/msitarzewski/agency-agents
- GEPA: https://github.com/gepa-ai/gepa · OpenEvolve: https://github.com/codelion/openevolve · DGM: https://github.com/jennyzzt/dgm · DGM paper: https://arxiv.org/abs/2505.22954
- Free LLM tiers (third-party, re-verify): https://openrouter.ai/blog/tutorials/free-llm-apis-compared/ · https://dev.to/tariqnasser/free-llm-api-tiers-in-october-2026-whats-left-and-how-i-chain-them-227l · https://eesel.ai/blog/groq-pricing · https://pasqualepillitteri.it/en/news/6683/gemini-2-5-flash-free-1m-tokens
- GitHub Models retirement: https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-july-30-2026/
- Frameworks: https://www.firecrawl.dev/blog/best-open-source-agent-frameworks · https://langfuse.com/blog/2025-03-19-ai-agent-comparison
- Evals: https://aicoolies.com/comparisons/promptfoo-vs-inspect-ai · https://qaskills.sh/blog/promptfoo-vs-deepeval-2026
- Memory: https://hindsight.vectorize.io/blog/2026/08/11/open-source-agent-memory-systems
- Observability: https://futureagi.com/blog/arize-phoenix-vs-langfuse-2026/
- Hosting free tiers: https://flaviocopes.com/hosting-free-tiers/ · https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026.md
- Claude Code plugins: https://www.morphllm.com/claude-code-marketplace · Subscription auth caveats: https://claudefa.st/blog/guide/development/claude-code-subscription
- UI: https://github.com/CopilotKit/CopilotKit
