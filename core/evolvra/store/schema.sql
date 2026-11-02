-- Evolvra system of record. SQLite, versioned by PRAGMA user_version.
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS agents (
  id              INTEGER PRIMARY KEY,
  slug            TEXT NOT NULL UNIQUE,
  name            TEXT NOT NULL,
  division        TEXT NOT NULL,
  emoji           TEXT,
  color           TEXT,
  current_version INTEGER NOT NULL DEFAULT 1,
  created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS agent_versions (
  id             INTEGER PRIMARY KEY,
  agent_id       INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  version        INTEGER NOT NULL,
  parent_version INTEGER,                      -- NULL for the upstream original
  content_md     TEXT NOT NULL,
  content_sha    TEXT NOT NULL,
  created_by     TEXT NOT NULL,                -- 'import' | 'evolve' | 'human'
  rationale      TEXT,
  source_json    TEXT,                         -- upstream repo/commit/path for imports
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE (agent_id, version)
);

CREATE TABLE IF NOT EXISTS missions (
  id          INTEGER PRIMARY KEY,
  external_id TEXT UNIQUE,                     -- mission dir name from the plugin
  brief       TEXT NOT NULL,
  mode        TEXT NOT NULL CHECK (mode IN ('micro','sprint','full')),
  status      TEXT NOT NULL DEFAULT 'running',
  started_at  TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
  id               INTEGER PRIMARY KEY,
  mission_id       INTEGER NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
  agent_version_id INTEGER NOT NULL REFERENCES agent_versions(id),
  input            TEXT NOT NULL,
  output           TEXT,
  attempt          INTEGER NOT NULL DEFAULT 1,
  verdict          TEXT,                       -- PASS | FAIL | NEEDS_WORK | NULL
  output_dir       TEXT,
  created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS traces (
  id          INTEGER PRIMARY KEY,
  task_id     INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
  session_id  TEXT,
  event       TEXT NOT NULL,
  tool        TEXT,
  args_json   TEXT,
  result_json TEXT,
  agent       TEXT,
  ts          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id);

CREATE TABLE IF NOT EXISTS scores (
  id            INTEGER PRIMARY KEY,
  task_id       INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  metric        TEXT NOT NULL,                 -- 'lint' | 'tests' | 'rubric:clarity' | 'reviewer'
  value         REAL NOT NULL,                 -- normalized 0..1
  evidence_json TEXT,
  judge_model   TEXT,                          -- NULL for deterministic checks
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS evolutions (
  id                      INTEGER PRIMARY KEY,
  agent_id                INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  parent_version          INTEGER NOT NULL,
  candidate_versions_json TEXT NOT NULL,
  winner_version          INTEGER,             -- NULL when no candidate beat the parent
  bank_delta              REAL,                -- winner fitness minus parent fitness on held-out bank
  diagnosis_md            TEXT,
  created_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Free-tier safety: per-provider daily request counters and a response cache.
CREATE TABLE IF NOT EXISTS provider_usage (
  provider TEXT NOT NULL,
  day      TEXT NOT NULL,                      -- YYYY-MM-DD in UTC
  requests INTEGER NOT NULL DEFAULT 0,
  tokens   INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (provider, day)
);

CREATE TABLE IF NOT EXISTS llm_cache (
  key           TEXT PRIMARY KEY,              -- sha256(provider|model|messages|params)
  provider      TEXT NOT NULL,
  model         TEXT NOT NULL,
  response_json TEXT NOT NULL,
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

PRAGMA user_version = 1;
