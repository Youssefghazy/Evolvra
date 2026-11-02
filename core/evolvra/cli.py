"""`evolvra` command line. Thin wrapper over store / registry / router."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .missions import ingest
from .registry import personas
from .router import client, quota
from .store import db


def cmd_init(args) -> int:
    conn = db.connect(args.db)
    print(f"database ready: {args.db or db.default_db_path()} (schema v{db.schema_version(conn)})")
    print(f"evolvra home:   {db.evolvra_home()}")
    return 0


def cmd_import(args) -> int:
    conn = db.connect(args.db)
    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"not a directory: {directory}", file=sys.stderr)
        return 2
    counts = personas.import_dir(conn, directory)
    print(" ".join(f"{k}={v}" for k, v in counts.items()))
    return 1 if counts["invalid"] else 0


def cmd_lint(args) -> int:
    bad = 0
    for p in personas.lint_dir(Path(args.directory)):
        status = "OK  " if p.ok else "FAIL"
        bad += not p.ok
        print(f"{status} {p.path.name}")
        for problem in p.problems:
            print(f"      error: {problem}")
        if args.verbose:
            for w in p.warnings:
                print(f"      warn:  {w}")
    return 1 if bad else 0


def cmd_agents(args) -> int:
    conn = db.connect(args.db)
    rows = personas.list_agents(conn)
    if args.json:
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("no agents yet. run: evolvra import ../plugin/agents")
        return 0
    width = max(len(r["slug"]) for r in rows)
    for r in rows:
        print(f"{r['emoji'] or '  '} {r['slug']:<{width}}  v{r['current_version']}  {r['division']}")
    return 0


def cmd_lineage(args) -> int:
    conn = db.connect(args.db)
    rows = personas.lineage(conn, args.slug)
    if not rows:
        print(f"unknown agent: {args.slug}", file=sys.stderr)
        return 2
    for r in rows:
        parent = f"← v{r['parent_version']}" if r["parent_version"] else "(origin)"
        print(f"v{r['version']} {parent:<8} {r['created_by']:<7} {r['created_at']}  {r['content_sha'][:12]}")
        if r["rationale"]:
            print(f"    {r['rationale']}")
    return 0


def cmd_providers(args) -> int:
    conn = db.connect(args.db)
    configured = set(client.configured_providers())
    print(f"{'provider':<11}{'key':<6}{'used':>6}{'cap':>6}{'left':>6}  model")
    for s in quota.status(conn):
        key = "yes" if s["provider"] in configured else "no"
        print(f"{s['provider']:<11}{key:<6}{s['used']:>6}{s['cap']:>6}{s['remaining']:>6}"
              f"  {client.default_model(s['provider'])}")
    return 0


def cmd_models(args) -> int:
    try:
        ids = client.list_models(args.provider)
    except client.ProviderError as e:
        print(f"{args.provider}: {e}", file=sys.stderr)
        return 1
    current = client.default_model(args.provider)
    for mid in ids:
        mark = "  <- current default" if mid == current else ""
        print(f"{mid}{mark}")
    if current not in ids:
        print(f"\nwarning: default '{current}' is not in this list."
              f" Set EVOLVRA_MODEL_{args.provider.upper()}=<id> in .env", file=sys.stderr)
    return 0


def cmd_ping(args) -> int:
    conn = db.connect(args.db)
    try:
        res = client.chat(
            conn,
            [{"role": "user", "content": "Reply with exactly: pong"}],
            provider=args.provider,
            model=args.model,
            max_tokens=16,
            use_cache=False,
        )
    except (client.ProviderError, quota.QuotaExceeded) as e:
        print(f"{args.provider}: {e}", file=sys.stderr)
        return 1
    print(f"{res.provider}/{res.model}: {res.text.strip()!r}")
    return 0


def cmd_ingest(args) -> int:
    conn = db.connect(args.db)
    report = ingest.ingest_all(conn)
    print(report.summary())
    for path, why in report.missions_invalid:
        print(f"  invalid: {path}\n    {why}", file=sys.stderr)
    return 1 if report.missions_invalid else 0


def cmd_missions(args) -> int:
    conn = db.connect(args.db)
    rows = ingest.list_missions(conn, last=args.last)
    if args.json:
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("no missions yet. run a /evolvra:mission in Claude Code, then: evolvra ingest")
        return 0
    for r in rows:
        done = r["tasks_done"] or 0
        print(f"{r['status']:<9} {r['external_id']}  tasks {done}/{r['tasks']}  attempts {r['attempts'] or 0}")
        print(f"          {r['brief'][:90]}")
    return 0


def cmd_mission_show(args) -> int:
    conn = db.connect(args.db)
    m, tasks = ingest.mission_detail(conn, args.id)
    if not m:
        print(f"unknown mission: {args.id}", file=sys.stderr)
        return 2
    print(f"{m['external_id']}  [{m['mode']}] {m['status']}")
    print(f"brief:   {m['brief']}")
    print(f"started: {m['started_at']}  finished: {m['finished_at'] or '-'}")
    if m["summary"]:
        print(f"summary: {m['summary']}")
    for t in tasks:
        print(f"  #{t['task_no']} {t['agent_slug']:<20} {t['status']:<9} verdict={t['verdict'] or '-':<10}"
              f" attempts={t['attempts']} traces={t['trace_count']}")
        print(f"      {t['task']}")
        for a in json.loads(t["attempts_json"]):
            fb = f"  feedback: {a['feedback']}" if a.get("feedback") else ""
            print(f"      attempt {a['n']}: {a.get('verdict') or 'running'}{fb}")
    return 0


def cmd_stats(args) -> int:
    conn = db.connect(args.db)
    rows = ingest.agent_stats(conn)
    if not rows:
        print("no scored tasks yet")
        return 0
    print(f"{'agent':<22}{'tasks':>6}{'pass':>6}{'fail':>6}{'avg att':>9}")
    for r in rows:
        print(f"{r['agent_slug']:<22}{r['tasks']:>6}{r['passed'] or 0:>6}{r['failed'] or 0:>6}{r['avg_attempts']:>9}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="evolvra", description="Evolvra core. Survival of the promptest.")
    p.add_argument("--db", help="SQLite path (default: $EVOLVRA_HOME/evolvra.db)")
    p.add_argument("--version", action="version", version=f"evolvra {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create or migrate the database").set_defaults(fn=cmd_init)

    s = sub.add_parser("import", help="import persona .md files into the registry")
    s.add_argument("directory")
    s.set_defaults(fn=cmd_import)

    s = sub.add_parser("lint", help="validate persona files (agency-agents frontmatter rules)")
    s.add_argument("directory")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(fn=cmd_lint)

    s = sub.add_parser("agents", help="list the roster")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_agents)

    s = sub.add_parser("lineage", help="show version history of one agent")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_lineage)

    sub.add_parser("providers", help="free-tier quota headroom").set_defaults(fn=cmd_providers)

    sub.add_parser("ingest", help="load recorder output (missions + traces) into the database").set_defaults(
        fn=cmd_ingest)

    s = sub.add_parser("missions", help="list recent missions")
    s.add_argument("--last", type=int, default=10)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_missions)

    s = sub.add_parser("mission", help="inspect one mission")
    ms = s.add_subparsers(dest="mission_cmd", required=True)
    s2 = ms.add_parser("show")
    s2.add_argument("id")
    s2.set_defaults(fn=cmd_mission_show)

    sub.add_parser("stats", help="per-agent pass/fail counts from ingested missions").set_defaults(fn=cmd_stats)

    s = sub.add_parser("ping", help="send one tiny request to a provider")
    s.add_argument("provider", choices=sorted(client.PROVIDERS))
    s.add_argument("--model", help="override the model id for this call")
    s.set_defaults(fn=cmd_ping)

    s = sub.add_parser("models", help="list model ids your key can use at a provider")
    s.add_argument("provider", choices=sorted(client.PROVIDERS))
    s.set_defaults(fn=cmd_models)
    return p


def load_dotenv() -> Path | None:
    """Load the first `.env` found in the current directory or its parents.

    Existing environment variables always win. Lines are KEY=VALUE; quotes and
    `#` comments are allowed. Stdlib only, so beginners never need python-dotenv.
    """
    for directory in [Path.cwd(), *Path.cwd().parents]:
        candidate = directory / ".env"
        if candidate.is_file():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                if key and value and key not in os.environ:
                    os.environ[key] = value
            return candidate
    return None


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
