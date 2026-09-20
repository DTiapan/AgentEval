"""End-to-end integration tests for AgentEval CLI."""

import json
from pathlib import Path

from typer.testing import CliRunner

from agenteval.cli.main import app

runner = CliRunner()


def test_cli_version() -> None:
    """Test 'agenteval version' command output."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "AgentEval version 0.1.0" in result.stdout


def test_cli_run_order_success(tmp_path: Path) -> None:
    """Test running clean order processing scenario."""
    trace_out = tmp_path / "order_trace.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--scenario",
            "examples/scenarios/order_success.yaml",
            "--agent",
            "examples/agents/order_processor.py:run_agent",
            "--output",
            str(trace_out),
            "--live",
        ],
    )
    assert result.exit_code == 0
    assert "Evaluating Scenario: Clean Order Processing" in result.stdout
    assert "Final Verdict" in result.stdout
    assert "PASS" in result.stdout
    assert trace_out.exists()

    with open(trace_out, encoding="utf-8") as f:
        data = json.load(f)
    assert data["verdict"] == "PASS"
    assert len(data["steps"]) >= 2


def test_cli_run_order_chaos_recovery(tmp_path: Path) -> None:
    """Test running chaos injected scenario where agent retries and recovers."""
    trace_out = tmp_path / "chaos_trace.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--scenario",
            "examples/scenarios/order_chaos.yaml",
            "--agent",
            "examples/agents/order_processor.py:run_agent",
            "--output",
            str(trace_out),
        ],
    )
    assert result.exit_code == 0
    assert "PASS" in result.stdout
    assert trace_out.exists()

    with open(trace_out, encoding="utf-8") as f:
        data = json.load(f)
    assert data["verdict"] == "PASS"
    # Step 1 should contain error from 503
    step1_res = data["steps"][0]["tool_results"][0]
    assert step1_res["is_error"] is True


def test_cli_run_unverifiable_claim() -> None:
    """Test scenario with no environmental state assertions returns UNVERIFIABLE and exit code 1."""
    result = runner.invoke(
        app,
        [
            "run",
            "--scenario",
            "examples/scenarios/unverifiable_claim.yaml",
        ],
    )
    assert result.exit_code == 1
    assert "UNVERIFIABLE" in result.stdout


def test_cli_replay_command(tmp_path: Path) -> None:
    """Test replaying an existing trace file."""
    trace_out = tmp_path / "sample_trace.json"
    runner.invoke(
        app,
        [
            "run",
            "--scenario",
            "examples/scenarios/order_chaos.yaml",
            "--agent",
            "examples/agents/order_processor.py:run_agent",
            "--output",
            str(trace_out),
        ],
    )
    assert trace_out.exists()

    replay_result = runner.invoke(app, ["replay", str(trace_out)])
    assert replay_result.exit_code == 0
    assert "AgentEval Execution Replay" in replay_result.stdout

    # Test jump-to-fail
    replay_jump = runner.invoke(app, ["replay", str(trace_out), "--jump-to-fail"])
    assert replay_jump.exit_code == 0
    assert "Jumping directly to first failure at Step 1" in replay_jump.stdout


def test_cli_invalid_scenario_file() -> None:
    """Test CLI error handling for non-existent scenario file."""
    result = runner.invoke(app, ["run", "--scenario", "non_existent.yaml"])
    assert result.exit_code != 0
