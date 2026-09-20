"""Base agent adapter interface for Bring Your Own Agent (BYOA) execution."""

from abc import ABC, abstractmethod

from agenteval.core.models import StepRecord, ToolCall


class AgentAdapter(ABC):
    """Abstract interface wrapping any agent under evaluation."""

    @abstractmethod
    def step(
        self,
        user_prompt: str,
        history: list[StepRecord],
    ) -> tuple[str | None, list[ToolCall], bool]:
        """Execute one reasoning/action turn.

        Returns:
            tuple of (thought, tool_calls, is_finished)
        """
        pass
