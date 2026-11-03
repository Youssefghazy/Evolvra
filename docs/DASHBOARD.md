# Dashboard (Phase 4)

A static site on GitHub Pages, free, no backend. The database lives on your machine, so publishing is a
two-step loop you run whenever you want the public page to catch up:

```powershell
cd ~/Evolvra/core
uv run evolvra export                       # SQLite -> dashboard/public/data/*.json
cd ~/Evolvra
git add dashboard/public/data; git commit -m "data: refresh dashboard"; git push
```

The push triggers `.github/workflows/pages.yml`, which builds the site and deploys it to
`https://youssefghazy.github.io/Evolvra/`.

## One-time setup
GitHub → your repo → **Settings → Pages → Build and deployment → Source: GitHub Actions**. That's all.

## What the snapshots contain
| file | content |
|---|---|
| `summary.json` | counts, promotions, free-tier requests per provider, generated-at |
| `agents.json` | roster with every version's full persona text, fitness, top failure class |
| `missions.json` | missions, tasks, attempt logs, per-judge and ensemble scores, critiques |
| `evolutions.json` | each generation: candidates, targets, fitness, winner, delta, diagnosis |

No secrets are ever exported. Persona texts and mission outputs are included by design: they are the
portfolio.

## Local development
```bash
cd dashboard && npm install && npm run dev
```
