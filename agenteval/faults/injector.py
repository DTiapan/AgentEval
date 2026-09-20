"""Tool call proxy and fault injection layer for agent reliability evaluation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agenteval.adapters.tool import ToolAdapter
from agenteval.core.models import FailureClass, ToolCall, ToolResult


class FaultRule(BaseModel):
    """Specification for a fault injected into a target tool invocation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    trigger_step: int | None = Field(
        default=None, description="Step number on which to trigger, or None for any"
    )
    trigger_occurrence: int | None = Field(
        default=None,
        description="Which occurrence of this tool call triggers the fault, or None for any",
    )
    fault_type: FailureClass = Field(default=FailureClass.TOOL_FAILURE)
    inject_timeout: bool = Field(default=False)
    inject_status_code: int | None = Field(default=None)
    error_message: str | None = Field(default=None)
    delay_ms: float = Field(default=0.0)


class ToolFaultInjector:
    """Proxies and intercepts tool calls to inject chaos faults according to configured rules."""

    def __init__(self, target_adapter: ToolAdapter, rules: list[FaultRule] | None = None) -> None:
        self.target_adapter = target_adapter
        self.rules = rules or []
        self._tool_call_counts: dict[str, int] = {}
        self.injected_fault_count: int = 0
        self.injected_history: list[dict[str, Any]] = []

    def execute(self, call: ToolCall, step_number: int = 1) -> ToolResult:
        """Intercept tool call, check fault rules, and either return synthetic error or delegate."""
        self._tool_call_counts[call.tool_name] = self._tool_call_counts.get(call.tool_name, 0) + 1
        current_occurrence = self._tool_call_counts[call.tool_name]

        for rule in self.rules:
            if rule.tool_name != call.tool_name:
                continue
            if rule.trigger_step is not None and rule.trigger_step != step_number:
                continue
            if (
                rule.trigger_occurrence is not None
                and rule.trigger_occurrence != current_occurrence
            ):
                continue

            # Fault rule matches! Inject failure.
            self.injected_fault_count += 1
            error_msg = rule.error_message or "Simulated tool failure"
            if rule.inject_timeout and not rule.error_message:
                error_msg = f"Tool '{call.tool_name}' timed out after {rule.delay_ms or 5000}ms."
            elif rule.inject_status_code:
                error_msg = f"Tool '{call.tool_name}' returned HTTP {rule.inject_status_code}."

            fault_record = {
                "call_id": call.call_id,
                "tool_name": call.tool_name,
                "step_number": step_number,
                "occurrence": current_occurrence,
                "fault_type": rule.fault_type,
                "error_message": error_msg,
            }
            self.injected_history.append(fault_record)

            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                is_error=True,
                error_message=error_msg,
                latency_ms=rule.delay_ms,
                mutated_state=False,
            )

        # No fault matched, execute underlying tool cleanly
        return self.target_adapter.execute(call)
