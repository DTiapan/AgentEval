"""Integration tests for agenteval serve CLI command."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from agenteval.cli.main import app

runner = CliRunner()


@patch("uvicorn.run")
def test_cli_serve_default(mock_uvicorn: MagicMock) -> None:
    result = runner.invoke(app, ["serve", "--no-ui"])
    assert result.exit_code == 0
    assert "API only (--no-ui)" in result.stdout
    mock_uvicorn.assert_called_once()
    kwargs = mock_uvicorn.call_args[1]
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8766


@patch("uvicorn.run")
def test_cli_serve_custom_port_and_cors(mock_uvicorn: MagicMock) -> None:
    result = runner.invoke(
        app,
        [
            "serve",
            "--port",
            "9999",
            "--host",
            "0.0.0.0",
            "--cors-origins",
            "http://example.com",
            "--no-ui",
        ],
    )
    assert result.exit_code == 0
    mock_uvicorn.assert_called_once()
    kwargs = mock_uvicorn.call_args[1]
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 9999
