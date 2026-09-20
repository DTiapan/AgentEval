"""End-to-end integration tests for dynamic on-the-go persona synthesis and caching."""

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from agenteval.cli.main import app

runner = CliRunner()


def test_cli_plan_dynamic_persona_synthesis_and_caching() -> None:
    # 1. First run: should synthesize and cache
    res1 = runner.invoke(app, ["plan", "--endpoint", "http://localhost:8000/db-service"])
    assert res1.exit_code == 0
    assert "Dynamic Persona Synthesis" in res1.output
    assert "SRE Engineer" in res1.output or "Database Reliability" in res1.output

    # 2. Second run: should show CACHED
    res2 = runner.invoke(app, ["plan", "--endpoint", "http://localhost:8000/db-service"])
    assert res2.exit_code == 0
    assert "CACHED" in res2.output


def test_cli_run_dynamic_persona_auto_selection() -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {
            "thought": "Executed DB failover verification safely.",
            "tool_calls": [],
            "is_finished": True,
        }
    ).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = runner.invoke(app, ["run", "--endpoint", "http://localhost:8000/db-service"])
        assert res.exit_code in [0, 1]
        assert "Auto-selected Persona:" in res.output
        assert "Assurance Scorecard" in res.output
