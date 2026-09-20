"""Idempotency and duplicate side-effect scorer for agent retry safety."""

from dataclasses import dataclass

from agenteval.core.models import ToolCall, ToolResult


@dataclass
class IdempotencyEvaluationResult:
    """Outcome of idempotency and retry evaluation."""

    idempotency_score: float
    duplicate_side_effects: int
    total_retries: int
    unsafe_retries: int


class IdempotencyScorer:
    """Evaluates retry safety and detects duplicate side-effect mutations across tool calls."""

    def evaluate(
        self, tool_pairs: list[tuple[ToolCall, ToolResult]]
    ) -> IdempotencyEvaluationResult:
        """Analyze tool invocations to identify duplicate mutations on retry."""
        seen_calls: dict[str, list[tuple[ToolCall, ToolResult]]] = {}

        for call, result in tool_pairs:
            action_signature = f"{call.tool_name}:{sorted(call.arguments.items())}"
            if action_signature not in seen_calls:
                seen_calls[action_signature] = []
            seen_calls[action_signature].append((call, result))

        duplicate_side_effects = 0
        total_retries = 0
        unsafe_retries = 0

        for _sig, history in seen_calls.items():
            if len(history) <= 1:
                continue

            total_retries += len(history) - 1

            # Check if any retry caused repeated state mutations without safe idempotency key
            mutations_count = sum(1 for _, res in history if res.mutated_state)
            if mutations_count > 1:
                # Multiple mutations for identical tool call
                duplicate_side_effects += mutations_count - 1
                unsafe_retries += 1
            else:
                # Check idempotency keys on retries
                first_key = history[0][0].idempotency_key
                for call, _ in history[1:]:
                    if call.idempotency_key is None or call.idempotency_key != first_key:
                        unsafe_retries += 1

        # Score is penalized by duplicate side effects
        if duplicate_side_effects > 0:
            score = max(0.0, 1.0 - (0.5 * duplicate_side_effects))
        else:
            score = 1.0

        return IdempotencyEvaluationResult(
            idempotency_score=round(score, 2),
            duplicate_side_effects=duplicate_side_effects,
            total_retries=total_retries,
            unsafe_retries=unsafe_retries,
        )
