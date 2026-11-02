# evolvra (core)

Zero-dependency Python engine behind the Evolvra plugin.

```bash
uv venv && uv pip install -e ".[dev]"
evolvra init && evolvra import ../plugin/agents && evolvra agents
pytest
```

Modules: `store` (SQLite schema), `registry` (persona import, versions, lineage),
`router` (OpenAI-compatible client for Gemini / Groq / OpenRouter with daily quota guard and cache).
`evals` and `evolve` arrive in Phases 2 and 3.
