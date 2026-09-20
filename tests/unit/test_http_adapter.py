"""Unit tests for HTTPAdapter connecting external REST/chat endpoints."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agenteval.adapters.http import HTTPAdapter


def test_http_adapter_standard_payload() -> None:
    adapter = HTTPAdapter(endpoint_url="http://localhost:8000/chat")

    mock_response_data = {
        "thought": "I will check the system status.",
        "tool_calls": [{"name": "check_status", "arguments": {"system": "db"}}],
        "is_finished": False,
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        thought, tool_calls, is_finished = adapter.step("Deploy server", [])

        assert thought == "I will check the system status."
        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "check_status"
        assert tool_calls[0].arguments == {"system": "db"}
        assert is_finished is False
        assert mock_urlopen.called


def test_http_adapter_openai_format() -> None:
    adapter = HTTPAdapter(endpoint_url="http://localhost:8000/v1/chat/completions")

    openai_response = {
        "choices": [
            {
                "message": {
                    "content": "Server deployment completed successfully.",
                    "tool_calls": [],
                },
                "finish_reason": "stop",
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(openai_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        thought, tool_calls, is_finished = adapter.step("Finish task", [])

        assert thought == "Server deployment completed successfully."
        assert len(tool_calls) == 0
        assert is_finished is True


def test_http_adapter_plain_text_response() -> None:
    adapter = HTTPAdapter(endpoint_url="http://localhost:8000/simple")

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"reply": "Hello there!"}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        thought, tool_calls, is_finished = adapter.step("Greet me", [])

        assert thought == "Hello there!"
        assert len(tool_calls) == 0
        assert is_finished is True


def test_http_adapter_network_failure_raises() -> None:
    adapter = HTTPAdapter(endpoint_url="http://localhost:9999/down")

    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        with pytest.raises(RuntimeError, match="HTTP request failed"):
            adapter.step("Hello", [])
