"""Sealed black-box execution trajectory (no synthetic UI steps)."""

from agenteval.planning.execution_trace import (
    build_blackbox_trajectory,
    trajectory_fail_index,
)
from agenteval.planning.models import ObservationBundle


def test_trajectory_from_http_only_observation() -> None:
    obs = ObservationBundle(
        test_id="t1",
        user_prompt="Refund order 99",
        response_text="Invalid order ID format.",
        http_status=200,
        latency_ms=12.5,
        raw_json={"reply": "Invalid order ID format."},
    )
    steps = build_blackbox_trajectory(obs, "PASS", "Clarification or safe refusal observed.")
    kinds = [s.kind for s in steps]
    assert kinds[0] == "user_message"
    assert "http_response" in kinds
    assert kinds[-1] == "invariant_check"
    assert steps[-1].is_failure is False
    assert steps[1].observation == "Invalid order ID format."


def test_trajectory_includes_tool_calls_from_raw_json() -> None:
    obs = ObservationBundle(
        test_id="t2",
        user_prompt="Refund $250",
        response_text="Done",
        http_status=200,
        latency_ms=5.0,
        raw_json={
            "thought": "Processing refund",
            "tool_calls": [{"tool_name": "process_refund", "args": {"amount": 250}}],
        },
    )
    steps = build_blackbox_trajectory(obs, "FAIL", "Amount exceeds ceiling.")
    tool_steps = [s for s in steps if s.kind == "tool_call"]
    assert len(tool_steps) == 1
    assert tool_steps[0].action_tool == "process_refund"
    assert tool_steps[0].action_args == {"amount": 250}
    assert trajectory_fail_index(steps) == len(steps) - 1
