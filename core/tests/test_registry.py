from pathlib import Path

from evolvra.registry import personas
from evolvra.store import db

AGENTS_DIR = Path(__file__).resolve().parents[2] / "plugin" / "agents"


def test_starter_roster_is_lint_clean():
    loaded = personas.lint_dir(AGENTS_DIR)
    assert len(loaded) == 10
    assert all(p.ok for p in loaded), [(p.path.name, p.problems) for p in loaded if not p.ok]


def test_import_is_idempotent_and_versions_on_change(tmp_path):
    conn = db.connect(":memory:")
    first = personas.import_dir(conn, AGENTS_DIR)
    assert first["added"] == 10 and first["invalid"] == 0
    second = personas.import_dir(conn, AGENTS_DIR)
    assert second["skipped"] == 10 and second["added"] == 0

    # a changed persona becomes version 2 with lineage to version 1
    src = AGENTS_DIR / "engineering-frontend-developer.md"
    edited = tmp_path / src.name
    edited.write_text(src.read_text(encoding="utf-8") + "\n## Evolved\nBe more careful.\n", encoding="utf-8")
    personas.import_dir(conn, tmp_path, created_by="evolve")
    rows = personas.lineage(conn, "frontend-developer")
    assert [r["version"] for r in rows] == [1, 2]
    assert rows[1]["parent_version"] == 1 and rows[1]["created_by"] == "evolve"


def test_parse_frontmatter_handles_quotes_and_missing():
    fm, body = personas.parse_frontmatter('---\nname: "X"\ncolor: red\n---\nbody')
    assert fm == {"name": "X", "color": "red"} and body == "body"
    assert personas.parse_frontmatter("no frontmatter") == ({}, "no frontmatter")


def test_invalid_persona_is_rejected(tmp_path):
    (tmp_path / "bad-agent.md").write_text("---\nname: Bad\n---\nshort", encoding="utf-8")
    p = personas.load_persona(tmp_path / "bad-agent.md")
    assert not p.ok
    assert any("description" in x for x in p.problems)
    assert any("too short" in x for x in p.problems)
