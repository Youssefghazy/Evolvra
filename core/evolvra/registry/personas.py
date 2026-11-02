"""Persona files: parse agency-agents style Markdown, lint, import into the registry."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FRONTMATTER = ("name", "description", "color")
RECOMMENDED_SECTIONS = ("Identity", "Core Mission", "Critical Rules")
_FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


@dataclass
class Persona:
    path: Path
    frontmatter: dict[str, str]
    body: str
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.frontmatter.get("name", "")

    @property
    def slug(self) -> str:
        return slugify(self.name)

    @property
    def division(self) -> str:
        # upstream convention: <division>-<rest>.md
        return self.path.name.split("-", 1)[0]

    @property
    def content(self) -> str:
        return self.path.read_text(encoding="utf-8")

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    @property
    def ok(self) -> bool:
        return not self.problems


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Minimal YAML-subset parser: `key: value` lines only (what agency-agents uses)."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    data: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key.strip()] = value
    return data, text[m.end():]


def load_persona(path: Path) -> Persona:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    p = Persona(path=path, frontmatter=fm, body=body)
    if not fm:
        p.problems.append("missing YAML frontmatter")
    for key in REQUIRED_FRONTMATTER:
        if not fm.get(key):
            p.problems.append(f"frontmatter missing required field: {key}")
    if len(body.strip()) < 500:
        p.problems.append("body too short to be a real persona (<500 chars)")
    for section in RECOMMENDED_SECTIONS:
        if section.lower() not in body.lower():
            p.warnings.append(f"recommended section not found: {section}")
    return p


def lint_dir(directory: Path) -> list[Persona]:
    return [load_persona(p) for p in sorted(directory.glob("*.md"))]


def import_dir(conn: sqlite3.Connection, directory: Path, created_by: str = "import") -> dict[str, int]:
    """Import every valid persona in `directory`. Idempotent: unchanged content is skipped.

    Returns counters: added, updated, skipped, invalid.
    """
    manifest = _read_manifest(directory)
    counts = {"added": 0, "updated": 0, "skipped": 0, "invalid": 0}
    for persona in lint_dir(directory):
        if not persona.ok:
            counts["invalid"] += 1
            continue
        source = manifest.get(persona.path.name)
        result = upsert_persona(conn, persona, created_by=created_by, source=source)
        counts[result] += 1
    conn.commit()
    return counts


def upsert_persona(
    conn: sqlite3.Connection, persona: Persona, *, created_by: str, source: dict | None = None,
    rationale: str | None = None,
) -> str:
    row = conn.execute("SELECT id, current_version FROM agents WHERE slug = ?", (persona.slug,)).fetchone()
    fm = persona.frontmatter
    if row is None:
        cur = conn.execute(
            "INSERT INTO agents (slug, name, division, emoji, color) VALUES (?,?,?,?,?)",
            (persona.slug, persona.name, persona.division, fm.get("emoji"), fm.get("color")),
        )
        agent_id, version, parent = cur.lastrowid, 1, None
        outcome = "added"
    else:
        agent_id = row["id"]
        latest = conn.execute(
            "SELECT content_sha, version FROM agent_versions WHERE agent_id = ? AND version = ?",
            (agent_id, row["current_version"]),
        ).fetchone()
        if latest and latest["content_sha"] == persona.sha:
            return "skipped"
        version, parent = row["current_version"] + 1, row["current_version"]
        outcome = "updated"
    conn.execute(
        "INSERT INTO agent_versions (agent_id, version, parent_version, content_md, content_sha,"
        " created_by, rationale, source_json) VALUES (?,?,?,?,?,?,?,?)",
        (agent_id, version, parent, persona.content, persona.sha, created_by, rationale,
         json.dumps(source) if source else None),
    )
    conn.execute(
        "UPDATE agents SET current_version = ?, name = ?, emoji = ?, color = ? WHERE id = ?",
        (version, persona.name, fm.get("emoji"), fm.get("color"), agent_id),
    )
    return outcome


def list_agents(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT a.slug, a.name, a.division, a.emoji, a.current_version,"
        " (SELECT COUNT(*) FROM agent_versions v WHERE v.agent_id = a.id) AS versions"
        " FROM agents a ORDER BY a.division, a.slug"
    ).fetchall()


def lineage(conn: sqlite3.Connection, slug: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT v.version, v.parent_version, v.created_by, v.rationale, v.created_at, v.content_sha"
        " FROM agent_versions v JOIN agents a ON a.id = v.agent_id WHERE a.slug = ? ORDER BY v.version",
        (slug,),
    ).fetchall()


def _read_manifest(directory: Path) -> dict[str, dict]:
    path = directory / "MANIFEST.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {a["file"]: a.get("source", {}) for a in data.get("agents", [])}
