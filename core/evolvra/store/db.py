"""SQLite system of record. One file, WAL mode, schema applied idempotently."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SCHEMA_VERSION = 2

# Stepwise upgrades for existing databases. Fresh databases get schema.sql directly.
# v1 -> v2: missions/tasks/traces were redesigned around the recorder format before
# any real data existed, so they are rebuilt (agents, versions, quota, cache are kept).
MIGRATIONS: dict[int, str] = {
    2: """
        DROP TABLE IF EXISTS traces;
        DROP TABLE IF EXISTS scores;
        DROP TABLE IF EXISTS tasks;
        DROP TABLE IF EXISTS missions;
    """,
}


def evolvra_home() -> Path:
    """Directory for the DB, trace log, mission outputs. Override with EVOLVRA_HOME."""
    home = os.environ.get("EVOLVRA_HOME")
    path = Path(home).expanduser() if home else Path.home() / ".evolvra"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_db_path() -> Path:
    return evolvra_home() / "evolvra.db"


def connect(path: str | os.PathLike | None = None) -> sqlite3.Connection:
    """Open (and migrate) the database. Pass ':memory:' for tests."""
    target = ":memory:" if path == ":memory:" else str(path or default_db_path())
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current >= SCHEMA_VERSION:
        return
    for version in range(current + 1, SCHEMA_VERSION + 1):
        if version in MIGRATIONS and current > 0:
            conn.executescript(MIGRATIONS[version])
    # schema.sql is idempotent (IF NOT EXISTS) and stamps the current version.
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def schema_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]
