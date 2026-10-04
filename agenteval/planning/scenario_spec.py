"""Scenario-first test generation models (B2′)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DialogueMode(StrEnum):
    """How user messages are produced at run time."""

    SCRIPTED = "scripted"
    SIMULATED = "simulated"


class UserProfile(BaseModel):
    """Simulator-only persona metadata (not sent verbatim to the agent)."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    tone: str = Field(default="neutral", description="e.g. frustrated, polite, terse")
    expertise: str = Field(default="medium", description="low | medium | high")
    constraints: list[str] = Field(default_factory=list)


class ScenarioOracle(BaseModel):
    """Rubric oracle for scoring (v1)."""

    model_config = ConfigDict(extra="forbid")

    must: list[str] = Field(default_factory=list)
    must_not: list[str] = Field(default_factory=list)


class ScenarioSpec(BaseModel):
    """Declarative scenario: goal + profile + oracle; materialized to user_prompt."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    capability_id: str
    goal: str
    user_profile: UserProfile
    private_facts: dict[str, str] = Field(default_factory=dict)
    dialogue_mode: DialogueMode = DialogueMode.SIMULATED
    max_turns: int = Field(default=6, ge=1, le=32)
    opening_strategy: str = Field(
        default="direct_request",
        description="Hint for UserSimulator (e.g. vague_complaint_then_details)",
    )
    oracle: ScenarioOracle = Field(default_factory=ScenarioOracle)
    sample_seed: int = Field(default=0, ge=0)
    coverage_tags: list[str] = Field(default_factory=list)
    template_id: str | None = None
    failure_mode: str = ""
    category: str = "functional"

    def oracle_as_expected_behavior(self) -> str:
        parts: list[str] = []
        if self.oracle.must:
            parts.append("Must: " + "; ".join(self.oracle.must))
        if self.oracle.must_not:
            parts.append("Must not: " + "; ".join(self.oracle.must_not))
        return " ".join(parts) if parts else "Agent should satisfy the user goal safely."

    def to_metadata(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
