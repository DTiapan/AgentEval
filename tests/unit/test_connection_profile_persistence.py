"""Unit tests for Target Connection Profile Dual-Engine Persistence (Slice 13.4)."""

from pathlib import Path

from agenteval.db.connection import connect, init_schema
from agenteval.db.protocol import SuiteRepositoryProtocol
from agenteval.db.suite_repository import SQLiteSuiteRepository
from agenteval.planning.models import CandidateTest, SuiteManifest, TestPack
from agenteval.targets.models import AuthType, TargetConnectionProfile


def test_protocol_conformance() -> None:
    assert isinstance(SQLiteSuiteRepository, type)
    # Check that SQLiteSuiteRepository implements the protocol
    repo = SQLiteSuiteRepository(":memory:")
    try:
        assert isinstance(repo, SuiteRepositoryProtocol)
    finally:
        repo.close()


def test_sqlite_v4_migration_adds_connection_profile_columns(tmp_path: Path) -> None:
    db_file = tmp_path / "migration_test.db"
    conn = connect(db_file)
    try:
        init_schema(conn)

        # Verify columns exist
        sv_cols = [r[1] for r in conn.execute("PRAGMA table_info('suite_versions')").fetchall()]
        assert "connection_profile_json" in sv_cols

        ar_cols = [r[1] for r in conn.execute("PRAGMA table_info('assurance_runs')").fetchall()]
        assert "connection_profile_json" in ar_cols
    finally:
        conn.close()


def test_sqlite_suite_repository_persists_connection_profile(tmp_path: Path) -> None:
    db_file = tmp_path / "repo_test.db"
    repo = SQLiteSuiteRepository(db_file)
    try:
        profile = TargetConnectionProfile(
            endpoint_url="https://agent.test/chat",
            auth_type=AuthType.BEARER,
            token_secret="super-secret-token",
            custom_headers={"X-Tenant": "tenant-abc"},
        )
        profile_json = profile.model_dump_json()

        manifest = SuiteManifest(
            agent_id="test-agent-persist",
            version=1,
            requirements_fingerprint="fp123",
            created_at="2026-10-04T12:00:00Z",
            endpoint_profile="https://agent.test/chat",
        )
        pool = [
            CandidateTest(
                id="T01",
                capability_id="cap1",
                persona_id="p1",
                name="T1",
                user_prompt="prompt",
                expected_behavior="behavior",
            )
        ]
        pack = TestPack(
            agent_id="test-agent-persist",
            version=1,
            candidate_count=1,
            tests=pool,
        )

        repo.init_suite(
            manifest,
            pool,
            pack,
            connection_profile_json=profile_json,
        )

        # Verify persisted value in suite_versions
        conn = connect(db_file)
        try:
            row = conn.execute(
                "SELECT connection_profile_json FROM suite_versions WHERE agent_id = ?",
                ("test-agent-persist",),
            ).fetchone()
            assert row is not None
            assert row["connection_profile_json"] == profile_json
        finally:
            conn.close()

        # Initialize run with connection profile
        repo.initialize_run(
            agent_id="test-agent-persist",
            run_id="run-persist-1",
            suite_version=1,
            endpoint_url="https://agent.test/chat",
            connection_profile_json=profile_json,
        )

        conn = connect(db_file)
        try:
            run_row = conn.execute(
                "SELECT connection_profile_json FROM assurance_runs WHERE run_id = ?",
                ("run-persist-1",),
            ).fetchone()
            assert run_row is not None
            assert run_row["connection_profile_json"] == profile_json
        finally:
            conn.close()

    finally:
        repo.close()
