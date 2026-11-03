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
  external_id TEXT NOT NULL UNIQUE,            -- mission dir name written by plugin/scripts/mission.py
  brief       TEXT NOT NULL,
  mode        TEXT NOT NULL CHECK (mode IN ('micro','sprint','full')),
  status      TEXT NOT NULL,                   -- running | done | failed | escalated
  summary     TEXT,
  started_at  TEXT NOT NULL,
  finished_at TEXT,
  source_path TEXT,
  ingested_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS tasks (
  id               INTEGER PRIMARY KEY,
  mission_id       INTEGER NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
  task_no          INTEGER NOT NULL,
  agent_slug       TEXT NOT NULL,
  agent_version_id INTEGER REFERENCES agent_versions(id),  -- NULL if the slug is not in the registry
  task             TEXT NOT NULL,
  acceptance_json  TEXT NOT NULL DEFAULT '[]',
  depends_json     TEXT NOT NULL DEFAULT '[]',
  status           TEXT NOT NULL,              -- pending | running | done | escalated
  attempts         INTEGER NOT NULL DEFAULT 0,
  verdict          TEXT,                       -- verdict of the last attempt
  attempts_json    TEXT NOT NULL DEFAULT '[]',
  output_dir       TEXT,
  started_at       TEXT,
  finished_at      TEXT,
  UNIQUE (mission_id, task_no)
);

CREATE TABLE IF NOT EXISTS traces (
  id          INTEGER PRIMARY KEY,
  line_no     INTEGER NOT NULL UNIQUE,         -- position in traces.jsonl, makes ingest idempotent
  mission_id  INTEGER REFERENCES missions(id) ON DELETE SET NULL,
  task_id     INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
  session_id  TEXT,
  event       TEXT NOT NULL,
  tool        TEXT,
  args_json   TEXT,
  result_json TEXT,
  agent       TEXT,
  ts          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_traces_task ON traces(task_id);
CREATE INDEX IF NOT EXISTS idx_traces_mission ON traces(mission_id);

-- Small key/value state for ingestion (file offsets etc.)
CREATE TABLE IF NOT EXISTS ingest_state (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scores (
  id            INTEGER PRIMARY KEY,
  task_id       INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  metric        TEXT NOT NULL,                 -- 'lint' | 'tests' | 'rubric:clarity' | 'reviewer'
  value         REAL NOT NULL,                 -- normalized 0..1
  evidence_json TEXT,
  judge_model   TEXT NOT NULL DEFAULT 'deterministic',  -- 'deterministic' | 'ensemble' | provider/model
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scores_unique ON scores(task_id, metric, judge_model);

CREATE TABLE IF NOT EXISTS evolutions (
  id                      INTEGER PRIMARY KEY,
  agent_id                INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  parent_version          INTEGER NOT NULL,
  candidate_versions_json TEXT NOT NULL,
  winner_version          INTEGER,             -- NULL when no candidate beat the parent
  bank_delta              REAL,                -- best paired delta (candidate - parent) on shared bank tasks
  diagnosis_md            TEXT,
  parent_fitness          REAL,
  bank_json               TEXT,                -- held-out tasks used, with the parent's per-task fitness
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

PRAGMA user_version = 4;
