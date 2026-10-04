"""Sealed execution trajectory from black-box HTTP runs (no fictional steps)."""

from uuid import uuid4

from agenteval.planning.models import ExecutionStep, ObservationBundle


def _build_steps_for_bundle(
    obs: ObservationBundle,
    turn_suffix: str = "",
) -> list[ExecutionStep]:
    steps: list[ExecutionStep] = []
    steps.append(
        ExecutionStep(
            step_id=_sid(),
            kind="user_message",
            label=f"User message{turn_suffix}",
            observation=obs.user_prompt,
        )
    )

    data = obs.raw_json if isinstance(obs.raw_json, dict) else {}
    thought = data.get("thought")
    if thought is not None and str(thought).strip():
        steps.append(
            ExecutionStep(
                step_id=_sid(),
                kind="agent_thought",
                label=f"Agent thought{turn_suffix} (response payload)",
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
                    label=f"Tool call {idx + 1}{turn_suffix}",
                    action_tool=tool_name,
                    action_args=args,
                )
            )

    response_body = obs.response_text or ""
    if not thought and not tool_calls:
        steps.append(
            ExecutionStep(
                step_id=_sid(),
                kind="http_response",
                label=f"HTTP response body{turn_suffix}",
                observation=response_body,
                http_status=obs.http_status,
                latency_ms=obs.latency_ms,
            )
        )
    elif response_body.strip():
        steps.append(
            ExecutionStep(
                step_id=_sid(),
                kind="http_response",
                label=f"HTTP response{turn_suffix} (aggregated text)",
                observation=response_body,
                http_status=obs.http_status,
                latency_ms=obs.latency_ms,
            )
        )
    return steps


def build_blackbox_trajectory(
    observation: ObservationBundle,
    verdict: str,
    rationale: str,
) -> list[ExecutionStep]:
    """Derive replay steps only from observable run artifacts (single or multi-turn)."""
    steps: list[ExecutionStep] = []
    if observation.turn_observations:
        for turn_idx, turn_obs in enumerate(observation.turn_observations, 1):
            steps.extend(_build_steps_for_bundle(turn_obs, turn_suffix=f" (Turn {turn_idx})"))
    else:
        steps.extend(_build_steps_for_bundle(observation, turn_suffix=""))

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
