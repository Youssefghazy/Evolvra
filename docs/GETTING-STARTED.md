# Getting started (beginner friendly, Windows first, Mac notes included)

Total cost of everything below: **$0**. Never add a payment card anywhere.
Open **PowerShell** on Windows (Start menu → type `PowerShell`). On Mac, open **Terminal**.

---

## Part A — Install the tools (once)

| Tool | Why | Windows | Mac |
|---|---|---|---|
| **Git** | version control, and Claude Code needs Git Bash on Windows | https://git-scm.com/download/win → run installer, keep defaults | `xcode-select --install` |
| **Python 3.12+** | runs the Evolvra core | https://www.python.org/downloads/ → installer → **tick "Add python.exe to PATH"** | `brew install python` or python.org |
| **uv** | installs Python packages with zero fuss | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Node.js LTS** | needed by Claude Code | https://nodejs.org → LTS installer | `brew install node` |
| **Claude Code** | the runtime for the agency | `npm install -g @anthropic-ai/claude-code` | same |

Close and reopen the terminal after installing, then check everything:

```powershell
git --version
python --version
uv --version
node --version
claude --version
```

Each line should print a version. If one says "not recognized", that tool is not on your PATH; reinstall it and tick the PATH option.

---

## Part B — Clone the repo and run the core

```powershell
cd ~
git clone https://github.com/Youssefghazy/Evolvra.git
cd Evolvra/core
uv sync --extra dev
uv run evolvra init
uv run evolvra import ../plugin/agents
uv run evolvra agents
```

Expected: the last command prints 10 agents, each at `v1`.
`uv run` runs a command inside the project's own virtual environment, so you never need to "activate" anything.

Run the tests too, because perfectionists do:

```powershell
uv run pytest -q
```

Expected: `11 passed`.

---

## Part C — Free API keys and the `.env` file

### C1. Google AI Studio (Gemini)
1. Go to https://aistudio.google.com/apikey and sign in with a Google account.
2. Click **Create API key**. If it asks for a project, choose "Create API key in new project".
3. Copy the key (starts with `AIza`). Keep this tab open.
4. Do **not** click anything about billing. The free tier works without it.

### C2. Groq
1. Go to https://console.groq.com/keys and sign up (Google or GitHub login works).
2. Click **Create API Key**, name it `evolvra`, copy it (starts with `gsk_`).

### C3. Put the keys in `.env`
In the `Evolvra` folder (not `core`), copy the example file:

```powershell
cd ~/Evolvra
Copy-Item .env.example .env        # Mac: cp .env.example .env
notepad .env                       # Mac: open -e .env
```

Fill in the two lines and save:

```
GEMINI_API_KEY=AIza...your key...
GROQ_API_KEY=gsk_...your key...
```

`.env` is gitignored, so it can never be committed by accident. Never paste keys into chat, screenshots, or issues.

### C4. Prove the router works
```powershell
cd ~/Evolvra/core
uv run evolvra providers
uv run evolvra ping groq
uv run evolvra ping gemini
```

Expected: `providers` shows `key yes` for gemini and groq. Each `ping` prints something like
`groq/llama-3.3-70b-versatile: 'pong'`. Run `providers` again: `used` is now `1` for each. That counter is the
zero-cost safety net.

If `ping` fails with `HTTP 401`, the key is wrong or has a stray space. With `HTTP 429`, you hit the
provider's limit; wait a minute. With `network error`, check your internet or VPN.

---

## Part D — Install the plugin and run the first mission

1. Start Claude Code in the repo folder and log in with your Claude subscription:
   ```powershell
   cd ~/Evolvra
   claude
   ```
   The first run opens a browser to sign in. Choose your Claude account (not an API key).

2. Inside Claude Code, add the marketplace and install the plugin:
   ```
   /plugin marketplace add Youssefghazy/Evolvra
   /plugin install evolvra@evolvra
   ```
   Then type `/plugin` and confirm `evolvra` is listed as enabled. Restart Claude Code once (`/exit`, then `claude`) so hooks load.

3. Run the first mission:
   ```
   /evolvra:mission write a one-paragraph product description for a note-taking app
   ```
   Claude will plan, pick 1–3 agents, delegate, and finish with a 5-line summary.

4. Check what was recorded:
   ```powershell
   dir ~/.evolvra                     # Mac: ls ~/.evolvra
   dir ~/.evolvra/missions
   Get-Content ~/.evolvra/traces.jsonl -Tail 3     # Mac: tail -n 3 ~/.evolvra/traces.jsonl
   ```
   You should see a `missions/<timestamp>-...` folder with `mission.json` and a `traces.jsonl` with JSON lines.

---

## Part E — Hand the results back for Phase 1

Phase 1 designs trace ingestion against real data. Share these two things in chat (they contain no secrets):

- the contents of one `mission.json`
- the last ~20 lines of `traces.jsonl`

Or commit them yourself as samples:
```powershell
mkdir ~/Evolvra/docs/samples
copy ~/.evolvra/missions/<folder>/mission.json ~/Evolvra/docs/samples/
Get-Content ~/.evolvra/traces.jsonl -Tail 20 | Set-Content ~/Evolvra/docs/samples/traces.sample.jsonl
cd ~/Evolvra; git add docs/samples; git commit -m "docs: first real mission samples"; git push
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `uv : The term 'uv' is not recognized` | Close and reopen PowerShell. If still missing, rerun the uv installer. |
| `python` opens the Microsoft Store | Install from python.org and tick "Add to PATH"; in Settings → Apps → App execution aliases, turn off the Python aliases. |
| `claude` says Git Bash is required | Install Git for Windows (Part A) and reopen the terminal. |
| `/evolvra:mission` not found | Run `/plugin` to confirm it's installed and enabled; restart Claude Code. |
| `traces.jsonl` never appears | Hooks need a restart after install. Also check `python --version` works in Git Bash. |
