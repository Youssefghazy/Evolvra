"""SQLite system of record. One file, WAL mode, schema applied idempotently."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SCHEMA_VERSION = 4

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
    # v2 -> v3: scores become idempotent per (task, metric, judge). No scores existed before v3.
    3: """
        DROP TABLE IF EXISTS scores;
    """,
}


def _add_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    """ALTER TABLE ... ADD COLUMN, only if the table exists and the column does not."""
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not exists:
        return  # schema.sql will create the table with the column already present
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _migrate_v4(conn: sqlite3.Connection) -> None:
    _add_column(conn, "evolutions", "parent_fitness", "REAL")
    _add_column(conn, "evolutions", "bank_json", "TEXT")


MIGRATION_FUNCS = {4: _migrate_v4}


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
        if current == 0:
            continue  # fresh database: schema.sql below creates everything at the current version
        if version in MIGRATIONS:
            conn.executescript(MIGRATIONS[version])
        if version in MIGRATION_FUNCS:
            MIGRATION_FUNCS[version](conn)
    # schema.sql is idempotent (IF NOT EXISTS) and stamps the current version.
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def schema_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]
