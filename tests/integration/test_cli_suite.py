"""Integration tests for agenteval suite CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from agenteval.cli.main import app
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult

runner = CliRunner()

SAMPLE_PRD = """# Order Bot — Requirements

## Capabilities
- Process Order: Process orders with order_id and items
- Cancel Order: Cancel existing orders
"""


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "cli_suite_test.db"
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", f"sqlite:///{db_file}")


def test_cli_suite_init_no_args() -> None:
    result = runner.invoke(app, ["suite", "init"])
    assert result.exit_code == 1
    assert "Provide --prd or --manifest" in result.stdout


def test_cli_suite_init_with_prd(tmp_path: Path) -> None:
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(SAMPLE_PRD, encoding="utf-8")
    suite_root = tmp_path / "suites"

    result = runner.invoke(
        app,
        [
            "suite",
            "init",
            "--prd",
            str(prd_file),
            "--agent-id",
            "order-bot",
            "--suite-root",
            str(suite_root),
            "--max-tests",
            "3",
        ],
    )
    assert result.exit_code == 0
    assert "Suite initialized at" in result.stdout
    assert "candidate_pool:" in result.stdout
    assert (suite_root / "order-bot" / "suite.manifest.json").exists()


def test_cli_suite_run_no_suite(tmp_path: Path) -> None:
    suite_root = tmp_path / "suites"
    result = runner.invoke(
        app,
        ["suite", "run", "--agent-id", "missing-agent", "--suite-root", str(suite_root)],
    )
    assert result.exit_code == 1
    assert "No suite for 'missing-agent'" in result.stdout


@patch("agenteval.planning.blackbox_runner.BlackboxRunner.run_pack")
def test_cli_suite_run_success(mock_run_pack: MagicMock, tmp_path: Path) -> None:
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(SAMPLE_PRD, encoding="utf-8")
    suite_root = tmp_path / "suites"

    init_res = runner.invoke(
        app,
        [
            "suite",
            "init",
            "--prd",
            str(prd_file),
            "--agent-id",
            "order-bot",
            "--suite-root",
            str(suite_root),
            "--max-tests",
            "2",
        ],
    )
    assert init_res.exit_code == 0

    mock_run_pack.return_value = SuiteRunReport(
        run_id="run-cli-1",
        agent_id="order-bot",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                rationale="Handled properly",
                observation=ObservationBundle(
                    test_id="t1",
                    user_prompt="Order item",
                    response_text="Order confirmed",
                    http_status=200,
                    latency_ms=15.0,
                ),
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )

    run_res = runner.invoke(
        app,
        [
            "suite",
            "run",
            "--agent-id",
            "order-bot",
            "--endpoint",
            "http://localhost:8000/chat",
            "--suite-root",
            str(suite_root),
        ],
    )
    assert run_res.exit_code == 0
    assert "Suite run run-cli-1" in run_res.stdout
    assert "Summary: 1 passed, 0 failed, 0 unverifiable" in run_res.stdout


@patch("agenteval.services.suite_workflow.SuiteWorkflow.generate_html_report")
def test_cli_suite_report(mock_gen_html: MagicMock, tmp_path: Path) -> None:
    mock_gen_html.return_value = "<html><body><h1>Report</h1></body></html>"
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(SAMPLE_PRD, encoding="utf-8")
    suite_root = tmp_path / "suites"

    runner.invoke(
        app,
        [
            "suite",
            "init",
            "--prd",
            str(prd_file),
            "--agent-id",
            "order-bot",
            "--suite-root",
            str(suite_root),
            "--max-tests",
            "2",
        ],
    )

    output_html = tmp_path / "out_report.html"
    res = runner.invoke(
        app,
        [
            "suite",
            "report",
            "--agent-id",
            "order-bot",
            "--suite-root",
            str(suite_root),
            "--output",
            str(output_html),
        ],
    )
    assert res.exit_code == 0
    assert "HTML report generated" in res.stdout
    assert output_html.exists()


def test_cli_suite_sync_no_suite(tmp_path: Path) -> None:
    manifest_file = tmp_path / "agent.yaml"
    manifest_file.write_text(
        "id: non-existent\nname: NonExistent\ncapabilities: []\n", encoding="utf-8"
    )
    suite_root = tmp_path / "suites"

    res = runner.invoke(
        app,
        [
            "suite",
            "sync",
            "--agent-id",
            "non-existent",
            "--manifest",
            str(manifest_file),
            "--suite-root",
            str(suite_root),
        ],
    )
    assert res.exit_code == 1
    assert "No suite for 'non-existent'" in res.stdout


def test_cli_suite_sync_noop(tmp_path: Path) -> None:
    manifest_file = tmp_path / "agent.yaml"
    manifest_file.write_text(
        "id: sync-bot\nname: Sync Bot\ncapabilities:\n  - name: Refund\n    description: Process refund\n",
        encoding="utf-8",
    )
    suite_root = tmp_path / "suites"

    init_res = runner.invoke(
        app,
        [
            "suite",
            "init",
            "--manifest",
            str(manifest_file),
            "--suite-root",
            str(suite_root),
            "--max-tests",
            "2",
        ],
    )
    assert init_res.exit_code == 0

    sync_res = runner.invoke(
        app,
        [
            "suite",
            "sync",
            "--agent-id",
            "sync-bot",
            "--manifest",
            str(manifest_file),
            "--suite-root",
            str(suite_root),
        ],
    )
    assert sync_res.exit_code == 0
    assert "Suite already matches manifest" in sync_res.stdout
