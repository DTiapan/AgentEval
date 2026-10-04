"""Integration tests for agenteval db CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from agenteval.cli.main import app
from agenteval.db.connection import connect, init_schema
from agenteval.planning.models import (
    CandidateTest,
    ObservationBundle,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.planning.suite_store import SuiteStore

runner = CliRunner()


def test_cli_db_import_suites_missing_dir(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist"
    result = runner.invoke(app, ["db", "import-suites", "--suite-root", str(non_existent)])
    assert result.exit_code == 1
    assert "Suite root not found" in result.stdout


def test_cli_db_import_suites_empty_dir(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty_suites"
    empty_dir.mkdir()
    result = runner.invoke(app, ["db", "import-suites", "--suite-root", str(empty_dir)])
    assert result.exit_code == 0
    assert "No suites found under" in result.stdout


def test_cli_db_import_suites_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    suite_root = tmp_path / "suites"
    store = SuiteStore(suite_root)
    manifest = SuiteStore.new_manifest("test-db-agent", "fp123", "http://localhost:8000")
    pool = [
        CandidateTest(
            id="t1",
            capability_id="c1",
            persona_id="p1",
            name="T1",
            user_prompt="Hello",
            expected_behavior="Reply",
        )
    ]
    pack = TestPack(
        agent_id="test-db-agent",
        tests=pool,
        candidate_count=1,
    )
    store.init_suite(manifest, pool, pack)

    report = SuiteRunReport(
        run_id="run-db-1",
        agent_id="test-db-agent",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                rationale="Success",
                observation=ObservationBundle(
                    test_id="t1",
                    user_prompt="Hello",
                    response_text="ok",
                    http_status=200,
                    latency_ms=10.0,
                ),
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    store.save_run("test-db-agent", report)

    db_path = tmp_path / "imported.db"
    result = runner.invoke(
        app,
        [
            "db",
            "import-suites",
            "--suite-root",
            str(suite_root),
            "--database",
            str(db_path),
        ],
    )
    assert result.exit_code == 0
    assert "Imported 1 agent(s)" in result.stdout
    assert db_path.is_file()


def test_cli_db_reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "reset_test.db"
    conn = connect(db_file)
    init_schema(conn)
    conn.close()
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", f"sqlite:///{db_file}")

    suite_dir = tmp_path / "suites_to_reset"
    suite_dir.mkdir()
    (suite_dir / "marker.txt").write_text("dummy")

    result = runner.invoke(
        app,
        ["db", "reset", "--yes", "--suite-root", str(suite_dir)],
    )
    assert result.exit_code == 0
    assert "Local engine data cleared" in result.stdout
    assert not db_file.exists()
    assert not suite_dir.exists()


def test_cli_db_reset_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "empty_nonexistent.db"
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", f"sqlite:///{db_file}")
    suite_dir = tmp_path / "no_suites"

    result = runner.invoke(
        app,
        ["db", "reset", "--yes", "--suite-root", str(suite_dir)],
    )
    assert result.exit_code == 0
    assert "Nothing to reset" in result.stdout
