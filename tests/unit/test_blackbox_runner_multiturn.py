"""Unit tests for sequential multi-turn blackbox runner execution and trajectories."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx

from agenteval.planning.blackbox_runner import BlackboxRunner
from agenteval.planning.models import CandidateTest, TestPack


def _make_mock_client(responses: list[dict[str, Any]]) -> tuple[httpx.Client, list[dict[str, Any]]]:
    captured_payloads: list[dict[str, Any]] = []
    response_idx = 0

    def mock_post(url: str, json: dict[str, Any] | None = None, **kwargs: Any) -> httpx.Response:
        nonlocal response_idx
        captured_payloads.append(json or {})
        resp_data = responses[min(response_idx, len(responses) - 1)]
        response_idx += 1
        request = httpx.Request("POST", url)
        return httpx.Response(status_code=200, json=resp_data, request=request)

    client = MagicMock(spec=httpx.Client)
    client.post.side_effect = mock_post
    return client, captured_payloads


def test_multiturn_sequential_invocation_and_history_accumulation() -> None:
    agent_responses = [
        {"reply": "Hello! How can I help you today?", "thought": "Greeting user."},
        {
            "reply": "Sure, could you please confirm order cancellation for #42?",
            "thought": "Prompting confirmation.",
        },
        {
            "reply": "Order #42 has been successfully cancelled.",
            "thought": "Executing cancellation.",
        },
    ]
    client, captured_payloads = _make_mock_client(agent_responses)

    runner = BlackboxRunner(
        endpoint_url="http://127.0.0.1:8766/chat",
        allow_private=True,
        client=client,
    )

    test = CandidateTest(
        id="test-multiturn-01",
        capability_id="order_cancellation",
        persona_id="standard_user",
        name="Multi-turn order cancellation",
        user_prompt="Hello",
        steps=["Hello", "I want to cancel order #42", "Yes, please confirm"],
        expected_behavior="Order #42 is cancelled successfully",
    )
    pack = TestPack(agent_id="test-agent", version=1, tests=[test], candidate_count=1)

    report = runner.run_pack(pack)
    assert len(report.results) == 1
    result = report.results[0]
    obs = result.observation

    # Verify 3 calls were made
    assert len(captured_payloads) == 3

    # Check Turn 1 payload
    assert captured_payloads[0]["prompt"] == "Hello"
    assert len(captured_payloads[0]["messages"]) == 1
    assert captured_payloads[0]["messages"][0]["content"] == "Hello"

    # Check Turn 2 payload has turn 1 in messages
    assert captured_payloads[1]["prompt"] == "I want to cancel order #42"
    assert len(captured_payloads[1]["messages"]) == 3
    assert captured_payloads[1]["messages"][1]["role"] == "assistant"
    assert "Hello! How can I help" in captured_payloads[1]["messages"][1]["content"]
    assert captured_payloads[1]["messages"][2]["content"] == "I want to cancel order #42"

    # Check Turn 3 payload has full transcript
    assert captured_payloads[2]["prompt"] == "Yes, please confirm"
    assert len(captured_payloads[2]["messages"]) == 5

    # Check ObservationBundle multi-turn details
    assert len(obs.turn_observations) == 3
    assert "successfully cancelled" in obs.response_text

    # Check trajectory steps
    assert result.trajectory is not None
    labels = [step.label for step in result.trajectory]
    assert "User message (Turn 1)" in labels
    assert "Agent thought (Turn 1) (response payload)" in labels
    assert "User message (Turn 2)" in labels
    assert "User message (Turn 3)" in labels
    assert "Invariant check" in labels[-1]


def test_multiturn_early_error_termination() -> None:
    client = MagicMock(spec=httpx.Client)
    req = httpx.Request("POST", "http://127.0.0.1:8766/chat")

    def mock_post_with_fail(
        url: str, json: dict[str, Any] | None = None, **kwargs: Any
    ) -> httpx.Response:
        prompt = (json or {}).get("prompt", "")
        if prompt == "Step 1":
            return httpx.Response(status_code=200, json={"reply": "Step 1 OK"}, request=req)
        return httpx.Response(status_code=500, text="Internal Server Error", request=req)

    client.post.side_effect = mock_post_with_fail

    runner = BlackboxRunner(
        endpoint_url="http://127.0.0.1:8766/chat",
        allow_private=True,
        client=client,
    )

    test = CandidateTest(
        id="test-multiturn-fail",
        capability_id="step_chain",
        persona_id="user",
        name="Multi-turn failure recovery",
        user_prompt="Step 1",
        steps=["Step 1", "Step 2", "Step 3"],
        expected_behavior="All steps pass",
    )
    pack = TestPack(agent_id="test-agent", version=1, tests=[test], candidate_count=1)
    report = runner.run_pack(pack)

    result = report.results[0]
    # Should record 2 turn observations (1 passed, 1 failed, 3rd not attempted)
    assert len(result.observation.turn_observations) == 2
    assert result.observation.http_status == 500
    assert result.verdict in ("FAIL", "UNVERIFIABLE")


def test_single_turn_backward_compatibility() -> None:
    client, captured_payloads = _make_mock_client([{"reply": "Direct response"}])
    runner = BlackboxRunner(
        endpoint_url="http://127.0.0.1:8766/chat",
        allow_private=True,
        client=client,
    )

    test = CandidateTest(
        id="test-single",
        capability_id="general",
        persona_id="user",
        name="Single turn",
        user_prompt="Single message",
        steps=[],
        expected_behavior="Reply received",
    )
    pack = TestPack(agent_id="test-agent", version=1, tests=[test], candidate_count=1)
    report = runner.run_pack(pack)

    result = report.results[0]
    assert len(result.observation.turn_observations) == 0
    assert result.observation.response_text == "Direct response"
    labels = [step.label for step in result.trajectory or []]
    assert "User message" in labels
    assert "User message (Turn 1)" not in labels
