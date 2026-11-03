# Evolvra dashboard

Static site: Vite + React 19 + Tailwind 4 + Recharts. No backend. It reads JSON snapshots from `public/data/`
that `evolvra export` writes from the SQLite database.

```bash
cd core && uv run evolvra export        # writes ../dashboard/public/data/*.json
cd ../dashboard && npm install && npm run dev
```

Views: Overview (KPIs, fitness chart, evolution queue) · Roster · Agent (genealogy, fitness by version,
version diff, persona) · Missions (tasks, attempts, per-judge scores, critiques) · Evolutions (candidates,
winners, diagnosis).

Deploys to GitHub Pages on every push that touches `dashboard/` (`.github/workflows/pages.yml`).
Enable once in the repo: Settings → Pages → Source: **GitHub Actions**.
