"""The evolution loop. Darwin's rule: a variant is promoted only if it beats its parent on held-out tasks."""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..registry import personas
from ..store import db
from . import bank as bank_mod
from . import diagnose as diagnose_mod
from . import mutate, tournament


class ReplayError(ValueError):
    """Same persona version and same diagnosis as the last generation: the cached proposals would replay it."""


def _lost_candidates(last) -> bool:
    """True when the last generation lost rewrites to provider errors (not to their own content). Errors are not
    cached, so a retry gets those rewrites for real instead of replaying; it is not a replay but an unfinished test.
    2026-11-06: two of three devops-automator rewrites never existed (HTTP 413 on Groq)."""
    try:
        cands = json.loads(last["candidate_versions_json"] or "[]")
    except (TypeError, ValueError):
        return False
    return any(any("mutator error" in str(p) for p in (c.get("problems") or [])) for c in cands if isinstance(c, dict))


@dataclass
class EvolveOptions:
    candidates: int = 3
    bank_size: int = 4
    margin: float = 0.03
    min_coverage: float = 0.75   # candidate and parent must both finish this share of the bank
    dry_run: bool = False
    mutator: tuple[str, str] | None = None
    actor: tuple[str, str] | None = None
    judges: list[tuple[str, str]] | None = None


@dataclass
class EvolveResult:
    slug: str
    parent_version: int
    evolution_dir: Path
    diagnosis: diagnose_mod.Diagnosis
    bank_size: int = 0
    parent_fitness: float | None = None
    candidates: list[dict] = field(default_factory=list)
    winner_index: int | None = None
    new_version: int | None = None
    delta: float | None = None
    coverage: int = 0
    dry_run: bool = False

    def summary(self) -> str:
        if self.dry_run:
            return (f"dry run: would evolve {self.slug} v{self.parent_version} with {len(self.candidates)} candidate(s)"
                    f" on {self.bank_size} bank task(s)")
        if self.winner_index is None:
            why = "no candidate completed enough shared tasks" if self.coverage == 0 else (
                f"best paired delta {self.delta:+} on {self.coverage} shared task(s) is below the margin")
            return f"no promotion: parent {self.slug} v{self.parent_version} fitness={self.parent_fitness}; {why}"
        return (f"PROMOTED {self.slug} v{self.parent_version} -> v{self.new_version}"
                f" (candidate {self.winner_index}, paired delta {self.delta:+} on {self.coverage} shared task(s),"
                f" fitness {self.parent_fitness} -> {self.candidates[self.winner_index - 1]['fitness']})")


def _manifest(plugin_agents_dir: Path) -> dict:
    return json.loads((plugin_agents_dir / "MANIFEST.json").read_text(encoding="utf-8"))


def _persona_file(plugin_agents_dir: Path, slug: str) -> Path:
    for a in _manifest(plugin_agents_dir)["agents"]:
        if a["slug"] == slug:
            return plugin_agents_dir / a["file"]
    raise ValueError(f"'{slug}' is not in {plugin_agents_dir / 'MANIFEST.json'}")


def evolve(conn: sqlite3.Connection, slug: str, plugin_agents_dir: Path, opts: EvolveOptions | None = None,
           *, home: Path | None = None, _transport=None) -> EvolveResult:
    opts = opts or EvolveOptions()
    home = home or db.evolvra_home()
    persona_path = _persona_file(plugin_agents_dir, slug)
    persona = personas.load_persona(persona_path)
    if not persona.ok:
        raise ValueError(f"current persona fails lint: {persona.problems}")
    personas.upsert_persona(conn, persona, created_by="import")  # make sure the DB knows the current file
    conn.commit()

    diag = diagnose_mod.diagnose(conn, slug)
    agent_row = conn.execute("SELECT id FROM agents WHERE slug = ?", (slug,)).fetchone()
    last = conn.execute(
        "SELECT diagnosis_md, candidate_versions_json FROM evolutions WHERE agent_id = ? AND parent_version = ?"
        " ORDER BY id DESC LIMIT 1", (agent_row["id"], diag.version)).fetchone()
    if last and last["diagnosis_md"] == diag.to_markdown() and not opts.dry_run and not _lost_candidates(last):
        raise ReplayError(f"{slug} v{diag.version}: nothing changed since its last generation (same persona, same"
                          " diagnosis); it would replay from cache")
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    evo_dir = home / "evolutions" / f"{stamp}-{slug}"
    evo_dir.mkdir(parents=True, exist_ok=True)
    (evo_dir / "diagnosis.md").write_text(diag.to_markdown(), encoding="utf-8")

    result = EvolveResult(slug, diag.version, evo_dir, diag, dry_run=opts.dry_run)
    held_out = bank_mod.load_bank(conn, plugin_agents_dir, slug, size=opts.bank_size)
    result.bank_size = len(held_out)
    if opts.dry_run:
        result.candidates = [{"index": i + 1, "target": t} for i, t in
                             enumerate(mutate.pick_targets(diag, opts.candidates))]
        return result
    if not held_out:
        raise ValueError(f"no bank tasks for '{slug}'; add plugin/agents/bank/{slug}.json or run missions")

    cands = mutate.propose(conn, persona.content, diag, k=opts.candidates, mutator=opts.mutator,
                           out_dir=evo_dir, _transport=_transport)
    desc = persona.frontmatter.get("description", "")
    parent_res = tournament.play(conn, persona.content, "parent", held_out, agent_slug=slug, agent_description=desc,
                                 actor=opts.actor, judges=opts.judges, _transport=_transport)
    result.parent_fitness = parent_res.fitness
    _save_outputs(evo_dir, parent_res)

    best_i, best_delta, best_cov = None, None, 0
    need = max(1, round(opts.min_coverage * len(held_out)))
    for c in cands:
        entry = {"index": c.index, "target": c.target, "path": str(c.path) if c.path else None,
                 "lint_ok": c.lint_ok, "problems": c.problems or [], "sha": c.sha, "fitness": None,
                 "paired_delta": None, "shared_tasks": 0, "per_task": []}
        if c.lint_ok and c.content:
            res = tournament.play(conn, c.content, f"candidate-{c.index}", held_out, agent_slug=slug,
                                  agent_description=desc, actor=opts.actor, judges=opts.judges, _transport=_transport)
            _save_outputs(evo_dir, res)
            delta, shared = tournament.paired_delta(res, parent_res)
            entry.update({"fitness": res.fitness, "paired_delta": delta, "shared_tasks": shared})
            entry["per_task"] = [{"task": r.task.task, "fitness": r.proxy_fitness, "failure": r.failure_class,
                                  "critique": r.critique, "scores": r.scores, "output_excerpt": r.output[:700]}
                                 for r in res.results]
            if delta is not None and shared >= need and (best_delta is None or delta > best_delta):
                best_i, best_delta, best_cov = c.index, delta, shared
        result.candidates.append(entry)

    promoted = best_i is not None and best_delta >= opts.margin
    result.delta, result.coverage = best_delta, best_cov

    agent_id = conn.execute("SELECT id FROM agents WHERE slug = ?", (slug,)).fetchone()["id"]
    if promoted:
        winner = next(c for c in cands if c.index == best_i)
        rationale = (f"evolved from v{diag.version}: targeted '{winner.target}'; paired delta {best_delta:+}"
                     f" on {best_cov} shared held-out task(s) (parent {result.parent_fitness})")
        persona_path.write_text(winner.content, encoding="utf-8")
        new_persona = personas.load_persona(persona_path)
        personas.upsert_persona(conn, new_persona, created_by="evolve", rationale=rationale)
        new_version = conn.execute("SELECT current_version FROM agents WHERE slug = ?", (slug,)).fetchone()[0]
        _bump_manifest(plugin_agents_dir, slug, new_version, diag.version, rationale)
        result.winner_index, result.new_version = best_i, new_version
    conn.execute(
        "INSERT INTO evolutions (agent_id, parent_version, candidate_versions_json, winner_version, bank_delta,"
        " diagnosis_md, parent_fitness, bank_json) VALUES (?,?,?,?,?,?,?,?)",
        (agent_id, diag.version, json.dumps(result.candidates, ensure_ascii=False),
         result.new_version, result.delta, diag.to_markdown(), result.parent_fitness,
         json.dumps([{"task": t.task, "source": t.source, "parent_fitness": parent_res.scored_tasks.get(t.key),
                      "parent_failure": r.failure_class, "parent_critique": r.critique,
                      "parent_output_excerpt": r.output[:700]}
                     for t, r in zip(held_out, parent_res.results, strict=True)], ensure_ascii=False)))
    conn.commit()
    (evo_dir / "report.md").write_text(_report(result, parent_res, held_out), encoding="utf-8")
    (evo_dir / "result.json").write_text(json.dumps({
        "slug": slug, "parent_version": diag.version, "parent_fitness": result.parent_fitness,
        "candidates": result.candidates, "winner_index": result.winner_index, "new_version": result.new_version,
        "delta": result.delta, "margin": opts.margin, "bank": [t.task for t in held_out]}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    return result


def _save_outputs(evo_dir: Path, res: tournament.PersonaResult) -> None:
    """Keep every actor output and its judge verdict on disk, so a surprising score can be audited."""
    folder = evo_dir / "arena" / res.label
    folder.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(res.results, start=1):
        head = (f"# {res.label} / task {i}\n\n**Task:** {r.task.task}\n\n**Proxy fitness:** {r.proxy_fitness}"
                f"  **Failure:** {r.failure_class}\n\n**Critique:** {r.critique}\n\n**Scores:** {r.scores}\n\n---\n\n")
        (folder / f"task-{i}.md").write_text(head + (r.output or "(no output)"), encoding="utf-8")


def _bump_manifest(plugin_agents_dir: Path, slug: str, version: int, parent: int, rationale: str) -> None:
    path = plugin_agents_dir / "MANIFEST.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for a in data["agents"]:
        if a["slug"] == slug:
            a["version"], a["parent"] = version, parent
            a.setdefault("history", []).append({"version": version, "parent": parent, "rationale": rationale,
                                                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    bump_plugin_version(plugin_agents_dir.parent)


def bump_plugin_version(plugin_dir: Path) -> str | None:
    """Patch-bump the plugin (and marketplace) version so `/plugin update` ships the promoted persona.

    Claude Code installs a cached copy; without a version change the installed roster keeps running the
    old persona while new tasks are credited to the new one (operator finding, 7c25923)."""
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest.exists():
        return None
    data = json.loads(manifest.read_text(encoding="utf-8"))
    parts = str(data.get("version", "0.0.0")).split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except ValueError:
        return None
    new = ".".join(parts)
    old = data.get("version")
    data["version"] = new
    manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    market = plugin_dir.parent / ".claude-plugin" / "marketplace.json"
    if market.exists():
        m = json.loads(market.read_text(encoding="utf-8"))
        for entry in m.get("plugins", []):
            if entry.get("name") == data.get("name") and entry.get("version") == old:
                entry["version"] = new
        m.setdefault("metadata", {})["version"] = new
        market.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return new


def _report(result: EvolveResult, parent_res: tournament.PersonaResult, held_out) -> str:
    lines = [f"# Evolution report: {result.slug} v{result.parent_version}", "", result.summary(), "",
             f"Held-out bank ({len(held_out)} tasks):"]
    lines += [f"{i + 1}. {t.task}  _(source: {t.source})_" for i, t in enumerate(held_out)]
    lines += ["", "## Fitness", "", "| persona | target | fitness | paired delta | shared tasks |", "|---|---|---|---|---|",
              f"| parent v{result.parent_version} | - | {result.parent_fitness} | - | - |"]
    for c in result.candidates:
        mark = " **winner**" if c["index"] == result.winner_index else ""
        note = c["fitness"] if c["lint_ok"] else f"failed: {'; '.join(c['problems'])[:120]}"
        lines.append(f"| candidate {c['index']}{mark} | {c['target']} | {note} | {c['paired_delta']} | {c['shared_tasks']} |")
    lines += ["", "## Parent per task", ""]
    lines += [f"- {r.task.task[:70]}: {r.proxy_fitness} `{r.failure_class}` {r.critique}" for r in parent_res.results]
    for c in result.candidates:
        if c["per_task"]:
            lines += ["", f"## Candidate {c['index']} ({c['target']}) per task", ""]
            lines += [f"- {p['task'][:70]}: {p['fitness']} `{p['failure']}` {p['critique']}" for p in c["per_task"]]
    return "\n".join(lines) + "\n"
