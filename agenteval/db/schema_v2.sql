-- AgentEval SQLite schema v2 (draft — see docs/design/persistence-schema.md)
-- Not applied by init_schema() until migration v002 ships.
PRAGMA foreign_keys = ON;

-- v1 tables: users, workspaces, workspace_members, agents, environments,
-- api_keys, audit_events — unchanged; include schema.sql before this file in migrations.

CREATE TABLE IF NOT EXISTS connectors (
    id            TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    slug          TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('http_transport','mcp_transport','db_diff','audit_log','trace')),
    config_json   TEXT NOT NULL DEFAULT '{}',
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
    manifest_json TEXT NOT NULL DEFAULT '{}',
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

-- suite_versions v2: migrate via ALTER in Alembic; full definition for greenfield installs
CREATE TABLE IF NOT EXISTS suite_versions_v2 (
    id                       TEXT PRIMARY KEY,
    agent_id                 TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version                  INTEGER NOT NULL CHECK (version >= 1),
    status                   TEXT NOT NULL CHECK (status IN ('draft','frozen')) DEFAULT 'draft',
    specification_version_id TEXT REFERENCES specification_versions(id),
    requirements_fingerprint TEXT NOT NULL,
    requirements_text        TEXT NOT NULL,
    endpoint_profile         TEXT NOT NULL DEFAULT '',
    candidate_pool_json      TEXT,
    agent_card_json          TEXT,
    pack_json                TEXT,
    frozen_at                TEXT,
    created_at               TEXT NOT NULL,
    created_by_user_id       TEXT REFERENCES users(id),
    UNIQUE (agent_id, version)
);

CREATE TABLE IF NOT EXISTS suite_pack_selections (
    suite_version_id TEXT NOT NULL REFERENCES suite_versions_v2(id) ON DELETE CASCADE,
    pack_id          TEXT NOT NULL REFERENCES packs(id),
    options_json     TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (suite_version_id, pack_id)
);

CREATE TABLE IF NOT EXISTS requirements (
    id               TEXT PRIMARY KEY,
    suite_version_id TEXT NOT NULL REFERENCES suite_versions_v2(id) ON DELETE CASCADE,
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
    suite_version_id TEXT NOT NULL REFERENCES suite_versions_v2(id) ON DELETE CASCADE,
    stable_id        TEXT NOT NULL,
    title            TEXT NOT NULL DEFAULT '',
    persona_json     TEXT NOT NULL DEFAULT '{}',
    inputs_json      TEXT NOT NULL DEFAULT '{}',
    test_data_json   TEXT NOT NULL DEFAULT '{}',
    UNIQUE (suite_version_id, stable_id)
);

CREATE TABLE IF NOT EXISTS test_case_criteria (
    test_case_id TEXT NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    criterion_id TEXT NOT NULL REFERENCES acceptance_criteria(id) ON DELETE CASCADE,
    PRIMARY KEY (test_case_id, criterion_id)
);

CREATE TABLE IF NOT EXISTS assurance_runs_v2 (
    run_id             TEXT PRIMARY KEY,
    agent_id           TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    suite_version_id   TEXT NOT NULL REFERENCES suite_versions_v2(id),
    target_id          TEXT NOT NULL REFERENCES targets(id),
    baseline_run_id    TEXT REFERENCES assurance_runs_v2(run_id),
    started_at         TEXT NOT NULL,
    finished_at        TEXT,
    status             TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed','cancelled')) DEFAULT 'queued',
    passed             INTEGER NOT NULL DEFAULT 0,
    failed             INTEGER NOT NULL DEFAULT 0,
    unverifiable       INTEGER NOT NULL DEFAULT 0,
    run_diff_json      TEXT,
    inspect_log_path   TEXT,
    inspect_log_sha256 TEXT,
    triggered_by       TEXT
);

CREATE TABLE IF NOT EXISTS case_executions (
    id               TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL REFERENCES assurance_runs_v2(run_id) ON DELETE CASCADE,
    test_case_id     TEXT NOT NULL REFERENCES test_cases(id),
    verdict_rollup   TEXT CHECK (verdict_rollup IN ('PASS','FAIL','UNVERIFIABLE')),
    rationale        TEXT NOT NULL DEFAULT '',
    observation_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE (run_id, test_case_id)
);

CREATE TABLE IF NOT EXISTS execution_steps_v2 (
    id                TEXT PRIMARY KEY,
    case_execution_id TEXT NOT NULL REFERENCES case_executions(id) ON DELETE CASCADE,
    step_index        INTEGER NOT NULL,
    step_id           TEXT NOT NULL,
    kind              TEXT NOT NULL,
    label             TEXT NOT NULL,
    thought           TEXT NOT NULL DEFAULT '',
    action_tool       TEXT NOT NULL DEFAULT '',
    action_args_json  TEXT NOT NULL DEFAULT '{}',
    observation       TEXT NOT NULL DEFAULT '',
    http_status       INTEGER,
    latency_ms        REAL,
    is_failure        INTEGER NOT NULL DEFAULT 0,
    UNIQUE (case_execution_id, step_index)
);

CREATE TABLE IF NOT EXISTS evidence_items (
    id                TEXT PRIMARY KEY,
    case_execution_id TEXT NOT NULL REFERENCES case_executions(id) ON DELETE CASCADE,
    connector_id      TEXT REFERENCES connectors(id),
    kind              TEXT NOT NULL,
    payload_json      TEXT NOT NULL,
    content_sha256    TEXT NOT NULL,
    captured_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS criterion_verdicts (
    id                TEXT PRIMARY KEY,
    case_execution_id TEXT NOT NULL REFERENCES case_executions(id) ON DELETE CASCADE,
    criterion_id      TEXT NOT NULL REFERENCES acceptance_criteria(id),
    verdict           TEXT NOT NULL CHECK (verdict IN ('PASS','FAIL','UNVERIFIABLE')),
    verdict_tier      TEXT NOT NULL CHECK (verdict_tier IN ('deterministic','model_judged')) DEFAULT 'deterministic',
    rationale         TEXT NOT NULL DEFAULT '',
    UNIQUE (case_execution_id, criterion_id)
);

CREATE TABLE IF NOT EXISTS criterion_verdict_evidence (
    verdict_id       TEXT NOT NULL REFERENCES criterion_verdicts(id) ON DELETE CASCADE,
    evidence_item_id TEXT NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
    PRIMARY KEY (verdict_id, evidence_item_id)
);

CREATE INDEX IF NOT EXISTS idx_connectors_workspace ON connectors(workspace_id);
CREATE INDEX IF NOT EXISTS idx_targets_agent ON targets(agent_id);
CREATE INDEX IF NOT EXISTS idx_requirements_suite ON requirements(suite_version_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_suite ON test_cases(suite_version_id);
CREATE INDEX IF NOT EXISTS idx_case_executions_run ON case_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_criterion_verdicts_execution ON criterion_verdicts(case_execution_id);
CREATE INDEX IF NOT EXISTS idx_evidence_execution ON evidence_items(case_execution_id);
