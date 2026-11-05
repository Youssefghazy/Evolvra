# Evolvra — instructions for any Claude Code session in this repo

Evolvra is a self-evolving AI agency: a Claude Code plugin (`plugin/`) runs specialist agents on missions,
a zero-dependency Python core (`core/`) scores them with free-tier judges and evolves the weakest persona,
and a static dashboard (`dashboard/`) publishes the results. Read `README.md`, then `docs/PLAN.md`,
`docs/SCORING.md`, `docs/EVOLUTION.md`, `docs/MISSION-FORMAT.md` before changing anything.

## Non-negotiable rules
1. **Zero spend.** Never attach a payment card, never enable billing, never use a paid API or paid tier.
   Free tiers only (Gemini, Groq, OpenRouter free models). Rate limits are hard stops, not upgrades.
2. **Secrets stay out of git.** Keys live only in `.env` (gitignored). Never print `.env`, never paste a key
   into a file, commit, log, STATUS note or chat.
3. **Model.** Run as Opus 5.5 (included in the Pro plan). Do not switch to a model that spends usage credits.
4. **Evidence over claims.** Nothing is "done" without the command and output that proves it. Tests must pass
   (`cd core && uv run pytest -q`, `uv run ruff check .`) before any commit that touches `core/`.
5. **Honest records.** Never edit mission.json, traces.jsonl or the SQLite DB by hand. Use the recorder
   (`plugin/scripts/mission.py`) and the CLI. If QA fails a builder, use `task reopen` so the retry counts.
6. **Small commits, clear messages, push to `main`.** Rebase on pull (`git pull --rebase`). Never force-push.

## This machine is a managed company PC (non-negotiable)
- **No downloads or installs** (npm, pip, browsers, validators, binaries) without Youssef's explicit OK in this
  session. On 2026-11-05 a validator run through Git Bash triggered 5 Trend Micro Apex One "Program Library
  Injection" alerts (MSYS fork), which the network admin had to report.
- **Use PowerShell, not Git Bash/MSYS `sh`**, to run anything. Prefer standard-library Python and tools already
  on the machine. If a check needs a tool that is not installed, say so and route it to a no-download method.
- In PowerShell 5.1, quote recorder arguments with single quotes; embedded double quotes get split.

## Daily operations (your machine has the DB, keys and Claude login; the cloud reviewer does not)
```powershell
cd ~/Evolvra
.\scripts\cycle.ps1            # ingest -> score -> export -> commit -> push
.\scripts\cycle.ps1 -Evolve    # same, plus one evolution generation on the weakest agent (~70-120 free calls)
cd core; uv run evolvra missions; uv run evolvra fitness; uv run evolvra lineage <slug>
```
Run missions with `/evolvra:mission <brief>` in Claude Code. Three missions per day across different agents
is a good pace. Vary the agents so fitness data covers the roster.

**After every `git pull` that touched `plugin/`, refresh the installed copy** (Claude Code caches plugins at
install time): inside Claude Code run `/plugin marketplace update evolvra` then `/plugin update evolvra@evolvra`,
and restart Claude Code. When you change `plugin/` yourself, bump `version` in `plugin/.claude-plugin/plugin.json`
and `.claude-plugin/marketplace.json` so the update is picked up.

## Handoff with the cloud reviewer (git is the channel)
- **You write `docs/STATUS.md`** at the end of every working session: what you ran, what happened (numbers),
  what broke, what you changed (commit SHAs), open questions. Overwrite it each time; history is in git.
- **The reviewer writes `docs/REVIEW.md`**: findings, requested changes, priorities. Read it at the start of
  every session and act on it. Mark items done in STATUS.md.
- The live dashboard is https://youssefghazy.github.io/Evolvra/ ; refresh it with `evolvra export` + push.

## Where things live
| path | purpose |
|---|---|
| `plugin/agents/*.md` | current persona files (evolution rewrites them; MANIFEST.json tracks versions) |
| `plugin/agents/bank/*.json` | held-out tasks per agent for the proxy tournament |
| `plugin/skills/*/SKILL.md` | the `/evolvra:*` commands |
| `plugin/scripts/mission.py`, `plugin/hooks/log_event.py` | recorder and trace hook (stdlib only) |
| `core/evolvra/{store,registry,router,missions,evals,evolve,export}.py` | the engine |
| `~/.evolvra/` | DB, traces, mission outputs, evolution reports and arena outputs (never committed) |
| `dashboard/public/data/*.json` | exported snapshots the site renders (committed by the cycle) |

## Things that bit us already (don't repeat)
- Groq free tier: 8k tokens/minute. Honor "try again in Ns". The actor role runs on Gemini Flash-Lite.
- Gemma rejects reasoning params (router remembers per model). Gemini 3.8 Flash times out on the free tier.
- Bank tasks must be self-contained; tasks that reference another task's files cannot be judged fairly.
- `git pull` without rebase opens an editor; `pull.rebase true` is set.
- Agents create `.venv`/`node_modules` inside output dirs; the scorer skips them (operator fix `20814d5`).
- Median judging let two lenient judges hide fabricated evidence; the ensemble is now a trimmed-low mean.
- Never "resume" an agent after a QA failure. `task done <qa> --verdict NEEDS_WORK` reopens the builder;
  relaunch it via `task start`. Work outside `task start` is off the record and the hook flags it.
