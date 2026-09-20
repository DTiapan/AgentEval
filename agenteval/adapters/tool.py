"""Tool adapter interface and local execution wrapper."""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from agenteval.core.models import ToolCall, ToolResult


class ToolAdapter(ABC):
    """Abstract interface for executing tools across different protocols."""

    @abstractmethod
    def execute(self, call: ToolCall) -> ToolResult:
        """Execute a tool call and return a structured ToolResult."""
        pass


class LocalToolAdapter(ToolAdapter):
    """Executes registered Python functions in-process."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        """Register a Python callable as an available tool."""
        self._tools[name] = func

    def execute(self, call: ToolCall) -> ToolResult:
        """Execute the tool if registered, measuring latency and catching errors."""
        if call.tool_name not in self._tools:
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                is_error=True,
                error_message=f"Tool '{call.tool_name}' is not registered in ToolAdapter.",
            )

        func = self._tools[call.tool_name]
        start_time = time.perf_counter()
        try:
            output = func(**call.arguments)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                output=output,
                is_error=False,
                latency_ms=round(elapsed_ms, 2),
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                is_error=True,
                error_message=f"Tool execution failed: {e!s}",
                latency_ms=round(elapsed_ms, 2),
            )
