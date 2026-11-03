# scripts

| script | what it does |
|---|---|
| `cycle.ps1 [-Evolve]` | pull, then `evolvra cycle`: ingest → score → (evolve weakest) → export → commit → push. Logs to `~/.evolvra/cycle.log`. |
| `schedule.ps1 [-Hours N] [-Evolve] [-Remove]` | registers/removes a Windows scheduled task that runs `cycle.ps1` every N hours. |

Once scheduled, nothing needs pasting: missions you run in Claude Code get scored, exported and pushed on
their own, the dashboard redeploys, and anyone (including a cloud Claude session) can read the results
straight from the repository.
