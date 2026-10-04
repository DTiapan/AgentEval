"""SQLite schema migrations (additive; v1 remains readable)."""

import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(r[1]) == column for r in rows)


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _migration_v002(conn: sqlite3.Connection) -> None:
    """Additive v2 tables and columns (see docs/design/persistence-schema.md)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            applied_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS connectors (
            id            TEXT PRIMARY KEY,
            workspace_id  TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            slug          TEXT NOT NULL,
            kind          TEXT NOT NULL CHECK (kind IN (
                'http_transport','mcp_transport','db_diff','audit_log','trace'
            )),
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

        CREATE TABLE IF NOT EXISTS suite_pack_selections (
            suite_version_id TEXT NOT NULL,
            pack_id          TEXT NOT NULL REFERENCES packs(id),
            options_json     TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (suite_version_id, pack_id)
        );

        CREATE TABLE IF NOT EXISTS requirements (
            id               TEXT PRIMARY KEY,
            suite_version_id TEXT NOT NULL,
            stable_id        TEXT NOT NULL,
            statement        TEXT NOT NULL,
            source_kind      TEXT NOT NULL CHECK (source_kind IN ('spec','pack')),
            source_pack_id   TEXT REFERENCES packs(id),
            review_status    TEXT NOT NULL CHECK (review_status IN (
                'proposed','approved','rejected'
            )) DEFAULT 'proposed',
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

        CREATE TABLE IF NOT EXISTS case_executions (
            id               TEXT PRIMARY KEY,
            run_id           TEXT NOT NULL REFERENCES assurance_runs(run_id) ON DELETE CASCADE,
            test_case_id     TEXT,
            verdict_rollup   TEXT CHECK (verdict_rollup IN ('PASS','FAIL','UNVERIFIABLE')),
            rationale        TEXT NOT NULL DEFAULT '',
            observation_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE (run_id, test_case_id)
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
            verdict_tier      TEXT NOT NULL CHECK (verdict_tier IN (
                'deterministic','model_judged'
            )) DEFAULT 'deterministic',
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
        """
    )

    if _table_exists(conn, "suite_versions"):
        _add_column_if_missing(
            conn, "suite_versions", "status", "status TEXT NOT NULL DEFAULT 'frozen'"
        )
        _add_column_if_missing(
            conn, "suite_versions", "specification_version_id", "specification_version_id TEXT"
        )
        _add_column_if_missing(conn, "suite_versions", "frozen_at", "frozen_at TEXT")

    if _table_exists(conn, "assurance_runs"):
        _add_column_if_missing(conn, "assurance_runs", "target_id", "target_id TEXT")
        _add_column_if_missing(conn, "assurance_runs", "baseline_run_id", "baseline_run_id TEXT")
        _add_column_if_missing(
            conn,
            "assurance_runs",
            "status",
            "status TEXT NOT NULL DEFAULT 'completed'",
        )
        _add_column_if_missing(conn, "assurance_runs", "inspect_log_path", "inspect_log_path TEXT")
        _add_column_if_missing(
            conn, "assurance_runs", "inspect_log_sha256", "inspect_log_sha256 TEXT"
        )
        _add_column_if_missing(conn, "assurance_runs", "error_message", "error_message TEXT")


def _migration_v003(conn: sqlite3.Connection) -> None:
    """Additive v3: error_message on assurance_runs for failed runs."""
    if _table_exists(conn, "assurance_runs"):
        _add_column_if_missing(conn, "assurance_runs", "error_message", "error_message TEXT")


def _migration_v004(conn: sqlite3.Connection) -> None:
    """Additive v4: connection_profile_json on suite_versions and assurance_runs (Slice 13)."""
    if _table_exists(conn, "suite_versions"):
        _add_column_if_missing(
            conn, "suite_versions", "connection_profile_json", "connection_profile_json TEXT"
        )
    if _table_exists(conn, "assurance_runs"):
        _add_column_if_missing(
            conn, "assurance_runs", "connection_profile_json", "connection_profile_json TEXT"
        )


def _migration_v005(conn: sqlite3.Connection) -> None:
    """Additive v5: run_jobs table for distributed background run status."""
    conn.executescript(
        """
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
        """
    )


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply pending migrations in order."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    current = int(row[0]) if row and row[0] is not None else 0

    from datetime import UTC, datetime

    if current < 2:
        _migration_v002(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (2, datetime.now(UTC).isoformat()),
        )
        conn.commit()

    if current < 3:
        _migration_v003(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (3, datetime.now(UTC).isoformat()),
        )
        conn.commit()

    if current < 4:
        _migration_v004(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (4, datetime.now(UTC).isoformat()),
        )
        conn.commit()

    if current < 5:
        _migration_v005(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (5, datetime.now(UTC).isoformat()),
        )
        conn.commit()
