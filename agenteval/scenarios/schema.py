"""Scenario schemas defining test tasks, assertions, and fault injection rules."""

from pydantic import BaseModel, ConfigDict, Field

from agenteval.evaluators.state_diff import StateDiffAssertion
from agenteval.faults.injector import FaultRule


class TestScenario(BaseModel):
    """Declarative specification for an agent evaluation scenario."""

    __test__ = False  # Prevent pytest from mistaking this as a test class
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    user_prompt: str
    expected_tools: list[str] = Field(default_factory=list)
    state_assertions: StateDiffAssertion | None = Field(default=None)
    fault_rules: list[FaultRule] = Field(default_factory=list)
    max_steps: int = Field(default=10, ge=1)
    allow_unverifiable: bool = Field(default=False)
