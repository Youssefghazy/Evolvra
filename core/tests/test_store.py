from evolvra.store import db


def test_schema_applies_and_is_idempotent():
    conn = db.connect(":memory:")
    assert db.schema_version(conn) == db.SCHEMA_VERSION
    db.migrate(conn)  # second run must be a no-op
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"agents", "agent_versions", "missions", "tasks", "traces", "scores",
            "evolutions", "provider_usage", "llm_cache"} <= tables
