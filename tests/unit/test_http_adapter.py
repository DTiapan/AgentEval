"""Unit tests for HTTPAdapter connecting external REST/chat endpoints."""

import httpx
import pytest

from agenteval.adapters.http import HTTPAdapter


def test_http_adapter_standard_payload() -> None:
    mock_response_data = {
        "thought": "I will check the system status.",
        "tool_calls": [{"name": "check_status", "arguments": {"system": "db"}}],
        "is_finished": False,
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=mock_response_data))
    client = httpx.Client(transport=transport)
    adapter = HTTPAdapter(endpoint_url="http://localhost:8000/chat", client=client)

    thought, tool_calls, is_finished = adapter.step("Deploy server", [])

    assert thought == "I will check the system status."
    assert len(tool_calls) == 1
    assert tool_calls[0].tool_name == "check_status"
    assert tool_calls[0].arguments == {"system": "db"}
    assert is_finished is False


def test_http_adapter_openai_format() -> None:
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
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=openai_response))
    client = httpx.Client(transport=transport)
    adapter = HTTPAdapter(endpoint_url="http://localhost:8000/v1/chat/completions", client=client)

    thought, tool_calls, is_finished = adapter.step("Finish task", [])

    assert thought == "Server deployment completed successfully."
    assert len(tool_calls) == 0
    assert is_finished is True


def test_http_adapter_plain_text_response() -> None:
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"reply": "Hello there!"}))
    client = httpx.Client(transport=transport)
    adapter = HTTPAdapter(endpoint_url="http://localhost:8000/simple", client=client)

    thought, tool_calls, is_finished = adapter.step("Greet me", [])

    assert thought == "Hello there!"
    assert len(tool_calls) == 0
    assert is_finished is True


def test_http_adapter_network_failure_raises() -> None:
    def error_transport(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = httpx.Client(transport=httpx.MockTransport(error_transport))
    adapter = HTTPAdapter(endpoint_url="http://localhost:9999/down", client=client)

    with pytest.raises(RuntimeError, match="HTTP request failed"):
        adapter.step("Hello", [])

