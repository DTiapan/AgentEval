-- AgentEval SQLite schema v1 (see docs/design/persistence-schema.md)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL DEFAULT '',
    password_hash TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    id         TEXT PRIMARY KEY,
    slug       TEXT NOT NULL UNIQUE,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role         TEXT NOT NULL CHECK (role IN ('OWNER','ADMIN','MEMBER','VIEWER')),
    created_at   TEXT NOT NULL,
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS agents (
    id           TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    slug         TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    UNIQUE (workspace_id, slug)
);

CREATE TABLE IF NOT EXISTS environments (
    id           TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    base_url     TEXT NOT NULL,
    is_default   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suite_versions (
    id                       TEXT PRIMARY KEY,
    agent_id                 TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version                  INTEGER NOT NULL CHECK (version >= 1),
    requirements_fingerprint TEXT NOT NULL,
    requirements_text        TEXT NOT NULL,
    endpoint_profile         TEXT NOT NULL DEFAULT '',
    connection_profile_json  TEXT,
    pack_json                TEXT NOT NULL,
    candidate_pool_json      TEXT,
    agent_card_json          TEXT,
    created_at               TEXT NOT NULL,
    created_by_user_id       TEXT REFERENCES users(id),
    UNIQUE (agent_id, version)
);

CREATE TABLE IF NOT EXISTS assurance_runs (
    run_id                  TEXT PRIMARY KEY,
    agent_id                TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    suite_version_id        TEXT NOT NULL REFERENCES suite_versions(id),
    environment_id          TEXT REFERENCES environments(id),
    endpoint_url            TEXT NOT NULL,
    connection_profile_json TEXT,
    started_at              TEXT NOT NULL,
    finished_at             TEXT NOT NULL,
    passed                  INTEGER NOT NULL DEFAULT 0,
    failed                  INTEGER NOT NULL DEFAULT 0,
    unverifiable            INTEGER NOT NULL DEFAULT 0,
    run_diff_json           TEXT,
    triggered_by            TEXT
);

CREATE TABLE IF NOT EXISTS test_case_results (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL REFERENCES assurance_runs(run_id) ON DELETE CASCADE,
    test_id          TEXT NOT NULL,
    verdict          TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL','UNVERIFIABLE')),
    rationale        TEXT NOT NULL DEFAULT '',
    observation_json TEXT NOT NULL,
    UNIQUE (run_id, test_id)
);

CREATE TABLE IF NOT EXISTS execution_steps (
    id                  TEXT PRIMARY KEY,
    test_case_result_id TEXT NOT NULL REFERENCES test_case_results(id) ON DELETE CASCADE,
    step_index          INTEGER NOT NULL,
    step_id             TEXT NOT NULL,
    kind                TEXT NOT NULL,
    label               TEXT NOT NULL,
    thought             TEXT NOT NULL DEFAULT '',
    action_tool         TEXT NOT NULL DEFAULT '',
    action_args_json    TEXT NOT NULL DEFAULT '{}',
    observation         TEXT NOT NULL DEFAULT '',
    http_status         INTEGER,
    latency_ms          REAL,
    is_failure          INTEGER NOT NULL DEFAULT 0,
    UNIQUE (test_case_result_id, step_index)
);

CREATE TABLE IF NOT EXISTS api_keys (
    id           TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    key_prefix   TEXT NOT NULL,
    key_hash     TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    revoked_at   TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id            TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    actor_user_id TEXT REFERENCES users(id),
    action        TEXT NOT NULL,
    entity_type   TEXT NOT NULL,
    entity_id     TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agents_workspace ON agents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_suite_versions_agent_version ON suite_versions(agent_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_runs_agent_started ON assurance_runs(agent_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_results_run ON test_case_results(run_id);
CREATE INDEX IF NOT EXISTS idx_steps_result ON execution_steps(test_case_result_id, step_index);
CREATE INDEX IF NOT EXISTS idx_audit_workspace_time ON audit_events(workspace_id, created_at DESC);

CREATE TABLE IF NOT EXISTS run_jobs (
    run_id       TEXT PRIMARY KEY,
    agent_id     TEXT NOT NULL,
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    started_at   TEXT,
    completed_at TEXT,
    completed    INTEGER NOT NULL DEFAULT 0,
    total        INTEGER NOT NULL DEFAULT 0,
    percent      REAL NOT NULL DEFAULT 0.0,
    error        TEXT
);

CREATE INDEX IF NOT EXISTS idx_run_jobs_agent ON run_jobs(agent_id, created_at DESC);
