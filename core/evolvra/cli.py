"""`evolvra` command line. Thin wrapper over store / registry / router."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
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
    print(f"{'provider':<11}{'key':<6}{'used':>6}{'cap':>6}{'left':>6}")
    for s in quota.status(conn):
        key = "yes" if s["provider"] in configured else "no"
        print(f"{s['provider']:<11}{key:<6}{s['used']:>6}{s['cap']:>6}{s['remaining']:>6}")
    return 0


def cmd_ping(args) -> int:
    conn = db.connect(args.db)
    try:
        res = client.chat(
            conn,
            [{"role": "user", "content": "Reply with exactly: pong"}],
            provider=args.provider,
            max_tokens=8,
            use_cache=False,
        )
    except (client.ProviderError, quota.QuotaExceeded) as e:
        print(f"{args.provider}: {e}", file=sys.stderr)
        return 1
    print(f"{res.provider}/{res.model}: {res.text.strip()!r}")
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

    s = sub.add_parser("ping", help="send one tiny request to a provider")
    s.add_argument("provider", choices=sorted(client.PROVIDERS))
    s.set_defaults(fn=cmd_ping)
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
