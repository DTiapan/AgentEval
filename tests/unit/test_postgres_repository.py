"""Unit tests verifying PostgreSQL persistence repository and factory routing (ADR-007)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agenteval.db.config import database_backend, get_database_url, is_postgres
from agenteval.db.postgres_repository import PostgresSuiteRepository
from agenteval.db.protocol import SuiteRepositoryProtocol
from agenteval.db.suite_repository import (
    SQLiteSuiteRepository,
    SuiteRepository,
    create_suite_repository,
)
from agenteval.planning.models import (
    CandidateTest,
    ExecutionStep,
    ObservationBundle,
    SuiteManifest,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.planning.run_diff import SuiteRunDiff
from agenteval.planning.suite_store import SuiteExistsError


def test_postgres_config_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify URL detection and backend determination."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTEVAL_DATABASE_URL", raising=False)

    assert get_database_url() == ""
    assert not is_postgres()
    assert database_backend() == "sqlite"

    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/agenteval")
    assert is_postgres()
    assert database_backend() == "postgres"

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/agenteval")
    assert is_postgres()
    assert database_backend() == "postgres"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", "postgresql://db.cloud.google.com/eval")
    assert is_postgres()
    assert database_backend() == "postgres"


def test_postgres_repository_missing_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify actionable ImportError if psycopg extra is missing."""
    with patch("agenteval.db.postgres_repository.HAS_PSYCOPG", False):
        with pytest.raises(ImportError, match="PostgreSQL support requires the 'postgres' extra"):
            PostgresSuiteRepository("postgresql://localhost:5432/db")


def test_postgres_repository_missing_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ValueError when no database URL is provided."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTEVAL_DATABASE_URL", raising=False)

    with pytest.raises(
        ValueError, match="PostgresSuiteRepository requires a valid PostgreSQL connection URL"
    ):
        PostgresSuiteRepository("")


def test_protocol_conformance() -> None:
    """Verify SQLite and Postgres repositories satisfy SuiteRepositoryProtocol."""
    assert issubclass(SQLiteSuiteRepository, SuiteRepositoryProtocol)
    assert issubclass(PostgresSuiteRepository, SuiteRepositoryProtocol)


def test_create_suite_repository_factory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify create_suite_repository routes to SQLite or Postgres based on parameters and environment."""
    sqlite_db = tmp_path / "test.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTEVAL_DATABASE_URL", raising=False)

    repo = create_suite_repository(sqlite_db)
    try:
        assert isinstance(repo, SQLiteSuiteRepository)
    finally:
        repo.close()

    # When URL is postgresql://
    with patch("agenteval.db.postgres_repository.ConnectionPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool

        pg_repo = create_suite_repository("postgresql://user:pass@localhost:5432/db")
        assert isinstance(pg_repo, PostgresSuiteRepository)
        assert pg_repo.database_url == "postgresql://user:pass@localhost:5432/db"

    # When environment has DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", "postgres://cloudsql/eval")
    with patch("agenteval.db.postgres_repository.ConnectionPool") as mock_pool_cls:
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool

        routed_repo = SuiteRepository()
        assert isinstance(routed_repo, PostgresSuiteRepository)
        assert routed_repo.database_url == "postgresql://cloudsql/eval"


def test_postgres_repository_mocked_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Comprehensive test of PostgresSuiteRepository lifecycle methods using mocked pool."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.execute.return_value = mock_cursor
    mock_pool = MagicMock()
    mock_pool.connection.return_value.__enter__.return_value = mock_conn

    with patch("agenteval.db.postgres_repository.ConnectionPool", return_value=mock_pool):
        repo = PostgresSuiteRepository("postgres://agenteval:secret@10.0.0.1:5432/evaldb")

        # 1. URL normalization
        assert repo.database_url == "postgresql://agenteval:secret@10.0.0.1:5432/evaldb"

        # 2. list_agent_ids
        mock_cursor.fetchall.return_value = [{"id": "agent-alpha"}, {"id": "agent-beta"}]
        agent_ids = repo.list_agent_ids()
        assert agent_ids == ["agent-alpha", "agent-beta"]

        # 3. delete_agent
        mock_cursor.fetchone.return_value = {"id": 1}
        assert repo.delete_agent("agent-alpha") is True
        mock_cursor.fetchone.return_value = None
        assert repo.delete_agent("missing-agent") is False

        # 4. ensure_default_target
        target_id = repo.ensure_default_target("agent-alpha", "http://127.0.0.1:8000")
        assert target_id == "agent-alpha-default-target"

        # 5. init_suite duplicate error vs force
        manifest = SuiteManifest(
            agent_id="agent-alpha",
            version=1,
            requirements_fingerprint="sha256:abc",
            created_at="2026-10-04T12:00:00Z",
            endpoint_profile="http",
        )
        pool = [
            CandidateTest(
                id="cand-1",
                capability_id="cap-1",
                persona_id="persona-1",
                name="Test Name",
                user_prompt="Hello",
                expected_behavior="Response",
            )
        ]
        pack = TestPack(
            agent_id="agent-alpha",
            version=1,
            tests=[],
            candidate_count=1,
            requirements_fingerprint="sha256:abc",
        )

        # Exists and not force -> raises SuiteExistsError
        mock_cursor.fetchone.return_value = {"1": 1}
        with pytest.raises(SuiteExistsError):
            repo.init_suite(manifest, pool, pack, force=False)

        # Force -> succeeds
        repo.init_suite(manifest, pool, pack, force=True, requirements_text="reqs text")

        # 6. load_manifest & load_pack & load_pool
        mock_cursor.fetchone.return_value = {
            "id": "agent-alpha-v1",
            "version": 1,
            "pack_json": pack.model_dump_json(),
            "candidate_pool_json": json.dumps([t.model_dump() for t in pool]),
            "agent_card_json": None,
            "requirements_fingerprint": "sha256:abc",
            "requirements_text": "reqs text",
            "endpoint_profile": "http",
            "created_at": "2026-10-04T12:00:00Z",
        }
        loaded_m = repo.load_manifest("agent-alpha")
        assert loaded_m.agent_id == "agent-alpha"
        assert loaded_m.version == 1

        loaded_p = repo.load_pack("agent-alpha")
        assert loaded_p.agent_id == "agent-alpha"

        loaded_pool = repo.load_pool("agent-alpha")
        assert len(loaded_pool) == 1
        assert loaded_pool[0].id == "cand-1"

        assert repo.load_requirements_text("agent-alpha") == "reqs text"

        # Missing agent suite raises FileNotFoundError
        mock_cursor.fetchone.return_value = None
        with pytest.raises(FileNotFoundError):
            repo.load_manifest("unknown")

        # 7. initialize_run & save_partial_result & finalize_run
        mock_cursor.fetchone.return_value = {"id": "agent-alpha-v1", "version": 1}
        suite_ver_id = repo.initialize_run(
            agent_id="agent-alpha",
            run_id="run-1",
            suite_version=1,
            endpoint_url="http://127.0.0.1:8000",
        )
        assert suite_ver_id == "agent-alpha-v1"

        test_result = TestCaseResult(
            test_id="cand-1",
            verdict="PASS",
            rationale="All assertions passed",
            observation=ObservationBundle(
                test_id="cand-1",
                user_prompt="Hello",
                response_text="200 OK",
            ),
            trajectory=[
                ExecutionStep(
                    step_id="step-1",
                    kind="action",
                    label="send request",
                    thought="calling api",
                    action_tool="http_client",
                    action_args={"method": "GET"},
                    observation="200 OK",
                    http_status=200,
                    latency_ms=15.2,
                    is_failure=False,
                )
            ],
        )

        repo.save_partial_result(
            run_id="run-1",
            result=test_result,
        )

        diff = SuiteRunDiff(
            baseline_run_id="run-0",
            baseline_suite_version=1,
            current_run_id="run-1",
            changes=[],
        )
        report = SuiteRunReport(
            agent_id="agent-alpha",
            run_id="run-1",
            suite_version=1,
            results=[test_result],
            passed=1,
            failed=0,
            unverifiable=0,
            run_diff=diff.model_dump(mode="json"),
        )

        mock_cursor.fetchone.return_value = {"1": 1}
        repo.finalize_run("agent-alpha", report, endpoint_url="http://127.0.0.1:8000")

        # 8. mark_run_failed & get_run_record
        repo.mark_run_failed(
            run_id="run-err",
            error_message="Network unreachable",
        )

        mock_cursor.fetchone.return_value = {
            "run_id": "run-err",
            "agent_id": "agent-alpha",
            "status": "failed",
            "error_message": "Network unreachable",
        }
        record = repo.get_run_record("run-err")
        assert record is not None
        assert record["status"] == "failed"
        assert record["error_message"] == "Network unreachable"

        # 9. load_latest_run
        # 9. load_latest_run
        mock_cursor.fetchone.side_effect = [
            # 1st query: SELECT run_id FROM assurance_runs
            {"run_id": "run-1"},
            # 2nd query in load_run: SELECT r.*, sv.version AS suite_version
            {
                "run_id": "run-1",
                "agent_id": "agent-alpha",
                "suite_version": 1,
                "passed": 1,
                "failed": 0,
                "unverifiable": 0,
                "run_diff_json": None,
                "status": "completed",
                "error_message": None,
            },
        ]
        mock_cursor.fetchall.side_effect = [
            # test_case_results rows
            [
                {
                    "id": 101,
                    "test_id": "cand-1",
                    "verdict": "PASS",
                    "rationale": "All assertions passed",
                    "observation_json": json.dumps(
                        {
                            "test_id": "cand-1",
                            "user_prompt": "Hello",
                            "response_text": "200 OK",
                        }
                    ),
                }
            ],
            # execution_steps rows
            [
                {
                    "step_index": 0,
                    "step_id": "step-1",
                    "kind": "action",
                    "label": "send request",
                    "thought": "calling api",
                    "action_tool": "http_client",
                    "action_args_json": {"method": "GET"},
                    "observation": "200 OK",
                    "http_status": 200,
                    "latency_ms": 15.2,
                    "is_failure": False,
                }
            ],
        ]

        latest_run = repo.load_latest_run("agent-alpha")
        assert latest_run is not None
        assert latest_run.run_id == "run-1"
        assert len(latest_run.results) == 1
        assert latest_run.results[0].test_id == "cand-1"
        assert len(latest_run.results[0].trajectory) == 1

        # 10. close
        repo.close()
        mock_pool.close.assert_called_once()


@patch("agenteval.db.postgres_repository.ConnectionPool")
def test_postgres_save_and_get_run_job(mock_pool_cls: MagicMock) -> None:
    from agenteval.services.run_manager import JobStatus, RunJobInfo, RunProgress

    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_pool.connection.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value = mock_cursor
    mock_pool_cls.return_value = mock_pool

    repo = PostgresSuiteRepository("postgresql://localhost/test")

    job = RunJobInfo(
        run_id="run-pg-123",
        agent_id="agent-pg",
        status=JobStatus.RUNNING,
        progress=RunProgress(completed=4, total=8, percent=50.0),
    )
    repo.save_run_job(job)
    mock_conn.execute.assert_called()

    # Mock get_run_job return
    mock_cursor.fetchone.return_value = {
        "run_id": "run-pg-123",
        "agent_id": "agent-pg",
        "status": "running",
        "created_at": "2026-10-04T12:00:00Z",
        "started_at": "2026-10-04T12:00:01Z",
        "completed_at": None,
        "completed": 4,
        "total": 8,
        "percent": 50.0,
        "error": None,
    }
    result = repo.get_run_job("run-pg-123")
    assert result is not None
    assert result.run_id == "run-pg-123"
    assert result.agent_id == "agent-pg"
    assert result.status == JobStatus.RUNNING
    assert result.progress.percent == 50.0
