"""In-process Python callable agent adapter."""

from collections.abc import Callable

from agenteval.adapters.base import AgentAdapter
from agenteval.core.models import StepRecord, ToolCall


class CallableAdapter(AgentAdapter):
    """Wraps an in-process Python function as an evaluatable agent."""

    def __init__(
        self,
        agent_fn: Callable[[str, list[StepRecord]], tuple[str | None, list[ToolCall], bool]],
        agent_id: str = "python-callable",
    ) -> None:
        self.agent_fn = agent_fn
        self.agent_id = agent_id

    def step(
        self,
        user_prompt: str,
        history: list[StepRecord],
    ) -> tuple[str | None, list[ToolCall], bool]:
        """Delegate reasoning turn to the provided agent callable."""
        return self.agent_fn(user_prompt, history)
