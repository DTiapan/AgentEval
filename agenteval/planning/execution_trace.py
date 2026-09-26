"""Sealed execution trajectory from black-box HTTP runs (no fictional steps)."""

from uuid import uuid4

from agenteval.planning.models import ExecutionStep, ObservationBundle


def build_blackbox_trajectory(
    observation: ObservationBundle,
    verdict: str,
    rationale: str,
) -> list[ExecutionStep]:
    """Derive replay steps only from observable run artifacts."""
    steps: list[ExecutionStep] = []
    steps.append(
        ExecutionStep(
            step_id=_sid(),
            kind="user_message",
            label="User message",
            observation=observation.user_prompt,
        )
    )

    data = observation.raw_json if isinstance(observation.raw_json, dict) else {}
    thought = data.get("thought")
    if thought is not None and str(thought).strip():
        steps.append(
            ExecutionStep(
                step_id=_sid(),
                kind="agent_thought",
                label="Agent thought (response payload)",
                thought=str(thought),
            )
        )

    tool_calls = data.get("tool_calls")
    if isinstance(tool_calls, list):
        for idx, call in enumerate(tool_calls):
            if not isinstance(call, dict):
                continue
            tool_name = str(call.get("tool_name") or call.get("name") or "unknown_tool")
            args = call.get("args") or call.get("arguments") or {}
            if not isinstance(args, dict):
                args = {"value": args}
            steps.append(
                ExecutionStep(
                    step_id=_sid(),
                    kind="tool_call",
                    label=f"Tool call {idx + 1}",
                    action_tool=tool_name,
                    action_args=args,
                )
            )

    response_body = observation.response_text or ""
    if not thought and not tool_calls:
        steps.append(
            ExecutionStep(
                step_id=_sid(),
                kind="http_response",
                label="HTTP response body",
                observation=response_body,
                http_status=observation.http_status,
                latency_ms=observation.latency_ms,
            )
        )
    elif response_body.strip():
        steps.append(
            ExecutionStep(
                step_id=_sid(),
                kind="http_response",
                label="HTTP response (aggregated text)",
                observation=response_body,
                http_status=observation.http_status,
                latency_ms=observation.latency_ms,
            )
        )

    steps.append(
        ExecutionStep(
            step_id=_sid(),
            kind="invariant_check",
            label="Invariant fail" if verdict == "FAIL" else "Invariant check",
            thought=rationale,
            observation=f"Verdict: {verdict}",
            http_status=observation.http_status,
            latency_ms=observation.latency_ms,
            is_failure=verdict == "FAIL",
        )
    )
    return steps


def trajectory_fail_index(steps: list[ExecutionStep]) -> int | None:
    for i, step in enumerate(steps):
        if step.is_failure:
            return i
    return None


def _sid() -> str:
    return uuid4().hex[:10]
