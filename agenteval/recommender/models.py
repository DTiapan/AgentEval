"""Domain models for metric recommendations and compiled evaluation plans."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentArchetype


class MetricRecommendation(BaseModel):
    """An individual evaluation metric recommended for an agent run."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Metric identifier (e.g. 'state_diff_delta_s')")
    plane: int = Field(ge=0, le=8, description="Target architecture plane (0 through 8)")
    group: Literal["UNIVERSAL_CORE", "DOMAIN_SPECIFIC"] = Field(
        description="Whether metric is mandatory for all agents or domain-activated"
    )
    description: str = Field(description="Why this metric is applied")
    evaluator_class: str = Field(description="Backing evaluator implementation class name")
    is_mandatory: bool = Field(default=False)


class EvaluationPlan(BaseModel):
    """Comprehensive, calibrated evaluation suite tailored to an agent's DNA."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(description="Target agent identifier")
    primary_archetype: AgentArchetype = Field(description="Resolved primary agent archetype")
    secondary_archetypes: list[AgentArchetype] = Field(
        default_factory=list, description="Additional capabilities detected in hybrid agents"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence of archetype classification")
    universal_metrics: list[MetricRecommendation] = Field(
        default_factory=list, description="Group A: Universal Core metrics"
    )
    domain_metrics: list[MetricRecommendation] = Field(
        default_factory=list, description="Group B: Domain-Specific metrics"
    )
    active_scorers: list[str] = Field(
        default_factory=list, description="Combined flat list of active evaluator names"
    )
    fault_suggestions: list[str] = Field(
        default_factory=list, description="Suggested chaos fault injection rules"
    )
