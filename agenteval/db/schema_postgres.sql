-- AgentEval PostgreSQL Production Schema (ADR-007)
-- Complete relational model with native JSONB support for multi-tenant Cloud Run deployments.

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
    connection_profile_json  JSONB,
    pack_json                JSONB NOT NULL,
    candidate_pool_json      JSONB,
    agent_card_json          JSONB,
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
    connection_profile_json JSONB,
    started_at              TEXT NOT NULL,
    finished_at             TEXT NOT NULL,
    passed                  INTEGER NOT NULL DEFAULT 0,
    failed                  INTEGER NOT NULL DEFAULT 0,
    unverifiable            INTEGER NOT NULL DEFAULT 0,
    run_diff_json           JSONB,
    triggered_by            TEXT,
    status                  TEXT,
    error_message           TEXT,
    target_id               TEXT
);

CREATE TABLE IF NOT EXISTS test_case_results (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL REFERENCES assurance_runs(run_id) ON DELETE CASCADE,
    test_id          TEXT NOT NULL,
    verdict          TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL','UNVERIFIABLE')),
    rationale        TEXT NOT NULL DEFAULT '',
    observation_json JSONB NOT NULL,
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
    action_args_json    JSONB NOT NULL DEFAULT '{}',
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
    metadata_json JSONB NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL
);

-- Connectors & Domain Packs (v2 schema)
CREATE TABLE IF NOT EXISTS connectors (
    id            TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    slug          TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('http_transport','mcp_transport','db_diff','audit_log','trace')),
    config_json   JSONB NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL,
    UNIQUE (workspace_id, slug)
);

CREATE TABLE IF NOT EXISTS targets (
    id                     TEXT PRIMARY KEY,
    workspace_id           TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    agent_id               TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    environment_id         TEXT REFERENCES environments(id),
    display_name           TEXT NOT NULL,
    transport_connector_id TEXT NOT NULL REFERENCES connectors(id),
    created_at             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS target_evidence_connectors (
    target_id    TEXT NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    connector_id TEXT NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    PRIMARY KEY (target_id, connector_id)
);

CREATE TABLE IF NOT EXISTS specifications (
    id           TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    slug         TEXT NOT NULL,
    title        TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    UNIQUE (workspace_id, slug)
);

CREATE TABLE IF NOT EXISTS specification_versions (
    id                 TEXT PRIMARY KEY,
    specification_id   TEXT NOT NULL REFERENCES specifications(id) ON DELETE CASCADE,
    version            INTEGER NOT NULL CHECK (version >= 1),
    body_text          TEXT NOT NULL,
    body_sha256        TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    created_by_user_id TEXT REFERENCES users(id),
    UNIQUE (specification_id, version)
);

CREATE TABLE IF NOT EXISTS packs (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    version       TEXT NOT NULL,
    manifest_json JSONB NOT NULL DEFAULT '{}',
    installed_at  TEXT NOT NULL,
    UNIQUE (name, version)
);

CREATE TABLE IF NOT EXISTS compliance_controls (
    id          TEXT PRIMARY KEY,
    pack_id     TEXT NOT NULL REFERENCES packs(id) ON DELETE CASCADE,
    control_key TEXT NOT NULL,
    title       TEXT NOT NULL,
    framework   TEXT NOT NULL DEFAULT '',
    UNIQUE (pack_id, control_key)
);

CREATE TABLE IF NOT EXISTS suite_pack_selections (
    suite_version_id TEXT NOT NULL,
    pack_id          TEXT NOT NULL REFERENCES packs(id),
    options_json     JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (suite_version_id, pack_id)
);

CREATE TABLE IF NOT EXISTS requirements (
    id               TEXT PRIMARY KEY,
    suite_version_id TEXT NOT NULL,
    stable_id        TEXT NOT NULL,
    statement        TEXT NOT NULL,
    source_kind      TEXT NOT NULL CHECK (source_kind IN ('spec','pack')),
    source_pack_id   TEXT REFERENCES packs(id),
    review_status    TEXT NOT NULL CHECK (review_status IN ('proposed','approved','rejected')) DEFAULT 'proposed',
    UNIQUE (suite_version_id, stable_id)
);

CREATE TABLE IF NOT EXISTS acceptance_criteria (
    id             TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    stable_id      TEXT NOT NULL,
    description    TEXT NOT NULL,
    evidence_kind  TEXT NOT NULL,
    check_kind     TEXT NOT NULL,
    source_kind    TEXT NOT NULL CHECK (source_kind IN ('extracted','pack','user')),
    source_pack_id TEXT REFERENCES packs(id),
    UNIQUE (requirement_id, stable_id)
);

CREATE TABLE IF NOT EXISTS criterion_compliance_map (
    criterion_id TEXT NOT NULL REFERENCES acceptance_criteria(id) ON DELETE CASCADE,
    control_id   TEXT NOT NULL REFERENCES compliance_controls(id) ON DELETE CASCADE,
    PRIMARY KEY (criterion_id, control_id)
);

CREATE TABLE IF NOT EXISTS test_cases (
    id               TEXT PRIMARY KEY,
    suite_version_id TEXT NOT NULL,
    stable_id        TEXT NOT NULL,
    title            TEXT NOT NULL DEFAULT '',
    persona_json     JSONB NOT NULL DEFAULT '{}',
    inputs_json      JSONB NOT NULL DEFAULT '{}',
    test_data_json   JSONB NOT NULL DEFAULT '{}',
    UNIQUE (suite_version_id, stable_id)
);

CREATE TABLE IF NOT EXISTS test_case_criteria (
    test_case_id TEXT NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    criterion_id TEXT NOT NULL REFERENCES acceptance_criteria(id) ON DELETE CASCADE,
    PRIMARY KEY (test_case_id, criterion_id)
);

CREATE TABLE IF NOT EXISTS criterion_verdicts (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL REFERENCES assurance_runs(run_id) ON DELETE CASCADE,
    criterion_id     TEXT NOT NULL REFERENCES acceptance_criteria(id) ON DELETE CASCADE,
    verdict          TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL','UNVERIFIABLE')),
    rationale        TEXT NOT NULL DEFAULT '',
    failing_test_ids TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL,
    UNIQUE (run_id, criterion_id)
);

CREATE TABLE IF NOT EXISTS criterion_evidence (
    id                  TEXT PRIMARY KEY,
    criterion_verdict_id TEXT NOT NULL REFERENCES criterion_verdicts(id) ON DELETE CASCADE,
    test_case_result_id TEXT REFERENCES test_case_results(id) ON DELETE CASCADE,
    kind                TEXT NOT NULL,
    payload_json        JSONB NOT NULL,
    created_at          TEXT NOT NULL
);

-- Performance & Query Indexes
CREATE INDEX IF NOT EXISTS idx_agents_workspace ON agents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_suite_versions_agent_version ON suite_versions(agent_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_runs_agent_started ON assurance_runs(agent_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_results_run ON test_case_results(run_id);
CREATE INDEX IF NOT EXISTS idx_steps_result ON execution_steps(test_case_result_id, step_index);
CREATE INDEX IF NOT EXISTS idx_audit_workspace_time ON audit_events(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_requirements_suite ON requirements(suite_version_id);
CREATE INDEX IF NOT EXISTS idx_criteria_requirement ON acceptance_criteria(requirement_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_suite ON test_cases(suite_version_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_run ON criterion_verdicts(run_id);

CREATE TABLE IF NOT EXISTS run_jobs (
    run_id       TEXT PRIMARY KEY,
    agent_id     TEXT NOT NULL,
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    started_at   TEXT,
    completed_at TEXT,
    completed    INTEGER NOT NULL DEFAULT 0,
    total        INTEGER NOT NULL DEFAULT 0,
    percent      DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    error        TEXT
);

CREATE INDEX IF NOT EXISTS idx_run_jobs_agent ON run_jobs(agent_id, created_at DESC);

