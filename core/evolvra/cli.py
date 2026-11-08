"""`evolvra` command line. Thin wrapper over store / registry / router."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import export as export_mod
from .evals import fitness, judge, runner
from .evolve import bank as bank_mod
from .evolve import engine
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
            max_tokens=256,
            use_cache=False,
        )
    except (client.ProviderError, quota.QuotaExceeded) as e:
        print(f"{args.provider}: {e}", file=sys.stderr)
        return 1
    usage = res.raw.get("usage") or {}
    print(f"{res.provider}/{res.model}: {res.text.strip()!r}"
          f"  (finish={res.finish_reason}, tokens={usage.get('total_tokens', '?')})")
    if not res.text.strip():
        print("warning: empty reply. The model probably spent its budget on hidden reasoning;"
              " try --model with a non-reasoning id or report this output.", file=sys.stderr)
        return 1
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


def cmd_score(args) -> int:
    conn = db.connect(args.db)
    tasks = runner.pending_tasks(conn, args.mission, rescore=args.rescore)
    if not tasks:
        print("nothing to score. run `evolvra ingest` first, or use --rescore")
        return 0
    judges = judge.judges_from_env()
    if args.judges:
        judges = [(p.strip(), m.strip()) for p, _, m in (x.partition(":") for x in args.judges.split(","))]
    print(f"scoring {len(tasks)} task(s) with judges: {', '.join(f'{p}/{m}' for p, m in judges)}"
          + ("  [deterministic only]" if args.no_judges else ""))
    if args.dry_run:
        for t in tasks:
            print(f"  would score {t['external_id']} #{t['task_no']} {t['agent_slug']}")
        return 0
    report = runner.score_tasks(conn, tasks, judges, skip_judges=args.no_judges)
    print(report.summary())
    for slug, no, f in report.fitness:
        print(f"  #{no} {slug:<22} fitness={f if f is not None else '-'}")
    return 0


def cmd_reaggregate(args) -> int:
    """Re-apply the current aggregation rules to stored judge rows. Zero API calls."""
    conn = db.connect(args.db)
    ids = [r["task_id"] for r in conn.execute(
        "SELECT DISTINCT task_id FROM scores WHERE judge_model = 'ensemble' ORDER BY task_id")]
    done, skipped, contested = 0, 0, 0
    for tid in ids:
        if judge.reaggregate(conn, tid):
            done += 1
        else:
            skipped += 1
    for r in conn.execute("SELECT t.agent_slug, t.task_no, m.external_id, json_extract(s.evidence_json,"
                          " '$.failure_class') AS fc, json_extract(s.evidence_json, '$.contested_by') AS by"
                          " FROM scores s JOIN tasks t ON t.id = s.task_id JOIN missions m ON m.id = t.mission_id"
                          " WHERE s.judge_model = 'ensemble' AND s.metric = 'rubric:correctness' AND by IS NOT NULL"):
        contested += 1
        print(f"  contested  {r['external_id']} #{r['task_no']} {r['agent_slug']:<20} {r['fc']}  (only {r['by']})")
    print(f"reaggregated {done} task(s), skipped {skipped} (a judge's rows are missing), "
          f"{contested} contested failure class(es); 0 API calls")
    return 0


def cmd_fitness(args) -> int:
    conn = db.connect(args.db)
    rows = fitness.agent_fitness(conn)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("no fitness yet. run: evolvra score")
        return 0
    print(f"{'agent':<22}{'ver':>4}{'tasks':>6}{'fitness':>9}{'min':>7}{'max':>7}  top failure")
    for r in rows:
        print(f"{r['agent']:<22}{r['version']:>4}{r['tasks']:>6}{r['fitness']:>9.3f}{r['min']:>7.2f}"
              f"{r['max']:>7.2f}  {r['top_failure'] or '-'}{' (contested)' if r.get('top_failure_contested') else ''}")
    return 0


def _plugin_agents_dir(args) -> Path:
    if args.plugin_dir:
        return Path(args.plugin_dir)
    here = Path(__file__).resolve()
    for parent in [Path.cwd(), *Path.cwd().parents, here.parents[2]]:
        cand = parent / "plugin" / "agents"
        if (cand / "MANIFEST.json").exists():
            return cand
    print("cannot find plugin/agents (run from the repo, or pass --plugin-dir)", file=sys.stderr)
    raise SystemExit(2)


def _pairs(spec: str | None):
    if not spec:
        return None
    return [(p.strip(), m.strip()) for p, _, m in (x.partition(":") for x in spec.split(",") if x.strip())]


def cmd_bank(args) -> int:
    conn = db.connect(args.db)
    tasks = bank_mod.load_bank(conn, _plugin_agents_dir(args), args.slug)
    if not tasks:
        print(f"no bank tasks for {args.slug}")
        return 1
    for i, t in enumerate(tasks, 1):
        print(f"{i}. [{t.source}] {t.task}")
        for c in t.acceptance:
            print(f"     - {c}")
    return 0


def cmd_evolve(args) -> int:
    conn = db.connect(args.db)
    opts = engine.EvolveOptions(candidates=args.candidates, bank_size=args.bank_size, margin=args.margin,
                                dry_run=args.dry_run, mutator=(_pairs(args.mutator) or [None])[0],
                                actor=(_pairs(args.actor) or [None])[0], judges=_pairs(args.judges))
    try:
        res = engine.evolve(conn, args.slug, _plugin_agents_dir(args), opts)
    except ValueError as e:
        print(f"evolve: {e}", file=sys.stderr)
        return 2
    print(res.summary())
    print(f"diagnosis: {res.evolution_dir / 'diagnosis.md'}")
    if res.dry_run:
        print(f"bank tasks: {res.bank_size}; targets: " + ", ".join(c["target"] for c in res.candidates))
        print("estimated calls: ~" + str((1 + len(res.candidates)) * res.bank_size * (1 + len(judge.judges_from_env()))
                                       + len(res.candidates)))
        return 0
    print(f"report:    {res.evolution_dir / 'report.md'}")
    for c in res.candidates:
        if c["lint_ok"]:
            status = f"fitness={c['fitness']}"
        elif any(str(x).startswith("mutator error") for x in c["problems"]):
            status = c["problems"][0]
        else:
            status = "lint failed: " + "; ".join(c["problems"])
        print(f"  candidate {c['index']} [{c['target']}]: {status}")
    if res.new_version:
        print("\nnew persona written to plugin/agents. Review with: git diff plugin/agents")
    return 0


def cmd_export(args) -> int:
    conn = db.connect(args.db)
    if args.out:
        out = Path(args.out)
    else:
        out = _plugin_agents_dir(args).parents[1] / "dashboard" / "public" / "data"
    counts = export_mod.export_all(conn, out)
    print(f"exported to {out}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    print("commit and push dashboard/public/data to update the live dashboard")
    return 0


def _git(repo: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(["git", "-C", str(repo), *args], check=False, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _hours_since_last_evolution(conn) -> float:
    row = conn.execute("SELECT MAX(created_at) AS t FROM evolutions").fetchone()
    if not row or not row["t"]:
        return 1e9
    from datetime import UTC, datetime
    last = datetime.fromisoformat(row["t"])
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return (datetime.now(UTC) - last).total_seconds() / 3600.0


def cmd_cycle(args) -> int:
    """ingest -> score -> (evolve weakest) -> export -> commit -> push. The no-hands loop."""
    conn = db.connect(args.db)
    plugin_dir = _plugin_agents_dir(args)
    repo = plugin_dir.parents[1]
    log = []

    rep = ingest.ingest_all(conn)
    log.append(f"ingest: {rep.summary()}")

    tasks = runner.pending_tasks(conn)
    if tasks:
        srep = runner.score_tasks(conn, tasks, judge.judges_from_env(), skip_judges=args.no_judges)
        log.append(f"score: {srep.summary()}")
    else:
        log.append("score: nothing new")

    # zero API calls: keeps every stored ensemble on the current aggregation rules before fitness is read
    ids = [r["task_id"] for r in conn.execute("SELECT DISTINCT task_id FROM scores WHERE judge_model = 'ensemble'")]
    log.append(f"reaggregate: {sum(judge.reaggregate(conn, t) for t in ids)}/{len(ids)} ensembles, 0 calls")

    evolved = None
    if args.evolve and _hours_since_last_evolution(conn) < args.evolve_interval:
        log.append(f"evolve: skipped, last generation ran {_hours_since_last_evolution(conn):.1f}h ago"
                   f" (interval {args.evolve_interval}h keeps Groq's daily token budget for scoring)")
        args.evolve = None
    if args.evolve:
        current = {r["slug"]: r["current_version"] for r in personas.list_agents(conn)}
        rows = [r for r in fitness.agent_fitness(conn)
                if r["tasks"] >= args.min_tasks and current.get(r["agent"]) == r["version"]]  # weakest first
        targets = [args.evolve] if args.evolve != "weakest" else [r["agent"] for r in rows]
        if not targets:
            log.append(f"evolve: no agent with >= {args.min_tasks} scored task(s) yet")
        for target in targets:
            try:
                res = engine.evolve(conn, target, plugin_dir, engine.EvolveOptions(
                    candidates=args.candidates, bank_size=args.bank_size, margin=args.margin))
                log.append(f"evolve: {res.summary()}")
                evolved = res if res.new_version else None
                break
            except engine.ReplayError as e:
                log.append(f"evolve: {e}; trying the next weakest")
            except ValueError as e:
                log.append(f"evolve: skipped ({e})")
                break

    out = repo / "dashboard" / "public" / "data"
    counts = export_mod.export_all(conn, out)
    log.append("export: " + ", ".join(f"{k}={v}" for k, v in counts.items()))

    push_failed = False
    if not args.no_push:
        paths = ["dashboard/public/data"]
        if evolved:
            # a promotion also bumps the plugin version (so `claude plugin update` delivers the new persona);
            # 8 Nov: those two files were left uncommitted, blocked the next pull and hid devops v2 from the plugin
            paths += ["plugin/agents", "plugin/.claude-plugin/plugin.json", ".claude-plugin/marketplace.json"]
        _git(repo, "add", *paths)
        code, status = _git(repo, "status", "--porcelain", *paths)
        if status:
            msg = f"cycle: refresh data ({counts['missions.json']} missions)"
            if evolved:
                msg = f"evolve({evolved.slug}): v{evolved.new_version} +{evolved.delta} | {msg}"
            # pathspec: commit only the cycle's own files, never something another session left staged
            # (2026-11-06: a half-finished headless STATUS.md rode along in a data commit)
            _git(repo, "commit", "-q", "-m", msg, "--", *paths)
            code, pushed = _git(repo, "push", "-q", "origin", "HEAD")
            if code != 0:  # remote moved on (e.g. new code pushed meanwhile): rebase our commit and retry once
                _git(repo, "pull", "-q", "--rebase", "--autostash", "origin", "main")
                code, pushed = _git(repo, "push", "-q", "origin", "HEAD")
            log.append("push: ok" if code == 0 else f"push failed: {pushed}")
            push_failed = code != 0
        else:
            log.append("push: nothing changed")
    for line in log:
        print(line)
    # 8 Nov: a rejected push still exited 0, so the scheduled task looked successful while a promotion sat unpushed
    return 1 if push_failed else 0


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

    s = sub.add_parser("score", help="score ingested tasks: deterministic checks + free-tier judge ensemble")
    s.add_argument("--mission", help="only this mission id")
    s.add_argument("--judges", help="override judges, e.g. groq:openai/gpt-oss-120b,gemini:gemma-4-31b-it")
    s.add_argument("--no-judges", action="store_true", help="deterministic checks only (no network)")
    s.add_argument("--rescore", action="store_true", help="re-score tasks that already have ensemble scores")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_score)

    sub.add_parser("reaggregate", help="re-apply aggregation rules to stored judge verdicts (no API calls)"
                   ).set_defaults(fn=cmd_reaggregate)

    s = sub.add_parser("fitness", help="fitness per agent version (what evolution optimizes)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_fitness)

    s = sub.add_parser("cycle", help="ingest -> score -> [evolve] -> export -> commit -> push, in one go")
    s.add_argument("--evolve", nargs="?", const="weakest", metavar="SLUG",
                   help="also run one evolution generation (default target: weakest agent)")
    s.add_argument("--min-tasks", type=int, default=1, help="min scored tasks before an agent may evolve")
    s.add_argument("--evolve-interval", type=float, default=12.0,
                   help="hours that must pass since the last generation before evolving again (default 12)")
    s.add_argument("--candidates", type=int, default=3)
    s.add_argument("--bank-size", type=int, default=4)
    s.add_argument("--margin", type=float, default=0.03)
    s.add_argument("--no-judges", action="store_true")
    s.add_argument("--no-push", action="store_true", help="do everything except git commit/push")
    s.add_argument("--plugin-dir")
    s.set_defaults(fn=cmd_cycle)

    s = sub.add_parser("export", help="write JSON snapshots for the dashboard (dashboard/public/data)")
    s.add_argument("--out", help="output directory (default: <repo>/dashboard/public/data)")
    s.add_argument("--plugin-dir")
    s.set_defaults(fn=cmd_export)

    s = sub.add_parser("bank", help="show an agent's held-out task bank")
    s.add_argument("slug")
    s.add_argument("--plugin-dir")
    s.set_defaults(fn=cmd_bank)

    s = sub.add_parser("evolve", help="diagnose, propose variants, proxy tournament, promote if it beats the parent")
    s.add_argument("slug")
    s.add_argument("--candidates", type=int, default=3)
    s.add_argument("--bank-size", type=int, default=4)
    s.add_argument("--margin", type=float, default=0.03, help="minimum fitness gain to promote")
    s.add_argument("--mutator", help="provider:model that writes variants (default groq:openai/gpt-oss-120b)")
    s.add_argument("--actor", help="provider:model that plays personas on bank tasks (default groq:openai/gpt-oss-120b)")
    s.add_argument("--judges", help="override judge ensemble, provider:model,...")
    s.add_argument("--plugin-dir", help="path to plugin/agents (auto-detected from the repo)")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_evolve)

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
