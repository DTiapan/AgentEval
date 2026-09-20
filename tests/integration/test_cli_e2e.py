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


def test_cli_plan_command_with_agent() -> None:
    """Test 'agenteval plan --agent <spec>' generates calibrated evaluation plan."""
    result = runner.invoke(
        app,
        ["plan", "--agent", "examples/agents/order_processor.py:run_agent"],
    )
    assert result.exit_code == 0
    assert "AgentEval Metric Recommender Plan" in result.stdout
    assert "TOOL_ACTION" in result.stdout
    assert "Group A: Universal Core Metrics" in result.stdout
    assert "Group B: Domain-Specific Metrics" in result.stdout
    assert "state_diff_delta_s" in result.stdout


def test_cli_plan_command_with_manifest(tmp_path: Path) -> None:
    """Test 'agenteval plan --manifest <path>' reads AgentCard and recommends plan."""
    manifest_file = tmp_path / "agenteval.manifest.yaml"
    manifest_file.write_text(
        """
id: "rag-assistant"
name: "Documentation Search"
archetype: "RAG"
capabilities:
  - name: "doc_qa"
    description: "Answers user questions using vector search"
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["plan", "--manifest", str(manifest_file)])
    assert result.exit_code == 0
    assert "rag-assistant" in result.stdout
    assert "RAG" in result.stdout
    assert "rag_faithfulness" in result.stdout
    assert "rag_context_precision" in result.stdout
