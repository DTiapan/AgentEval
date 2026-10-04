"""End-to-end CLI integration tests for Agency Personas, HTTP Endpoints, and PRD compilation."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from agenteval.cli.main import app

runner = CliRunner()


def test_cli_plan_with_agency_persona() -> None:
    result = runner.invoke(
        app,
        ["plan", "--persona", "examples/agency_personas/engineering-sre.md"],
    )
    assert result.exit_code == 0
    assert "Target Agent: engineering-sre" in result.output
    assert "TOOL_ACTION" in result.output
    assert "Group A: Universal Core Metrics" in result.output
    assert "Group B: Domain-Specific Metrics" in result.output
    assert "Dynamically Compiled Test Scenarios" in result.output


def test_cli_plan_with_sales_persona() -> None:
    result = runner.invoke(
        app,
        ["plan", "--persona", "examples/agency_personas/sales-deal-strategist.md"],
    )
    assert result.exit_code == 0
    assert "SUPPORT" in result.output
    assert "sales-deal-strategist" in result.output


def test_cli_plan_with_prd(tmp_path: Path) -> None:
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(
        "# Customer Service PRD\n1. Feature: Handle refund requests\n2. Feature: Check order status\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["plan", "--prd", str(prd_file)])
    assert result.exit_code == 0
    assert "Dynamically Compiled Test Scenarios" in result.output


def test_cli_plan_with_endpoint() -> None:
    result = runner.invoke(app, ["plan", "--endpoint", "http://localhost:8000/chat"])
    assert result.exit_code == 0
    assert "endpoint:http://localhost:8000/chat" in result.output


def test_cli_run_with_persona() -> None:
    result = runner.invoke(
        app,
        ["run", "--persona", "examples/agency_personas/engineering-sre.md"],
    )
    # The run executes the compiled scenario; default agent yields UNVERIFIABLE (exit code 1)
    assert result.exit_code in [0, 1]
    assert "Assurance Scorecard" in result.output
    assert "Trace auto-saved" in result.output


def test_cli_run_with_http_endpoint_and_persona() -> None:
    import httpx

    mock_resp = httpx.Response(
        200,
        json={
            "thought": "All automated rollbacks completed.",
            "tool_calls": [],
            "is_finished": True,
        },
    )

    with patch("httpx.Client.post", return_value=mock_resp):
        result = runner.invoke(
            app,
            [
                "run",
                "--endpoint",
                "http://localhost:8000/chat",
                "--persona",
                "examples/agency_personas/engineering-sre.md",
            ],
        )
        assert "Evaluating Scenario:" in result.output
        assert "Assurance Scorecard" in result.output
