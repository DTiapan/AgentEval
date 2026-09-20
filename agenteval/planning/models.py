"""Domain models for black-box test planning, optimization, and coverage."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceLayer(StrEnum):
    """How a fact in the Agent Test Model was obtained."""

    DECLARED = "DECLARED"
    INFERRED = "INFERRED"
    HYPOTHESIZED = "HYPOTHESIZED"


class MandatoryCategory(StrEnum):
    """Security/safety floors that optimization must not drop when applicable."""

    AUTHORIZATION = "authorization"
    DATA_ISOLATION = "data_isolation"
    SENSITIVE_DATA_LEAKAGE = "sensitive_data_leakage"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    PROMPT_INJECTION = "prompt_injection"
    TOOL_OUTPUT_INJECTION = "tool_output_injection"
    IRREVERSIBLE_ACTIONS = "irreversible_actions"
    CRITICAL_INVARIANTS = "critical_invariants"


class CandidateTest(BaseModel):
    """A single generated test candidate (pool member; not necessarily executed)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable test identifier")
    capability_id: str = Field(description="Declared capability this test exercises (for suite prune)")
    persona_id: str = Field(description="Persona slug or identifier")
    name: str = Field(description="Short human-readable title")
    user_prompt: str = Field(description="Input sent to the agent endpoint")
    expected_behavior: str = Field(
        description="Observable expectation (no internal state claims)"
    )
    coverage_tags: list[str] = Field(
        default_factory=list,
        description="Tags for set cover, e.g. cap:refund, persona:adversary, security:auth",
    )
    mandatory_categories: list[MandatoryCategory] = Field(
        default_factory=list,
        description="Mandatory floors this test satisfies when selected",
    )
    category: str = Field(default="functional", description="functional, security, reliability, …")
    failure_mode: str = Field(default="", description="Hypothesis under test")
    rationale: str = Field(default="", description="Why this test exists")
    template_id: str | None = Field(default=None, description="Rule template id if rule-generated")
    execution_cost: float = Field(default=1.0, ge=0.01, description="Relative cost weight for optimizer")
    is_mandatory: bool = Field(
        default=False,
        description="Always include in pack when present in pool",
    )


class TestPack(BaseModel):
    """Optimized subset of candidates chosen for execution."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    version: int = Field(default=1, ge=1)
    tests: list[CandidateTest] = Field(default_factory=list)
    candidate_count: int = Field(ge=0)
    requirements_fingerprint: str = Field(
        default="",
        description="Hash of PRD/manifest at generation time",
    )


class OptimizerConfig(BaseModel):
    """Parameters for weighted set-cover selection."""

    model_config = ConfigDict(extra="forbid")

    max_tests: int = Field(default=12, ge=1)
    applicable_mandatory: list[MandatoryCategory] = Field(
        default_factory=list,
        description="Mandatory floors that apply to this agent",
    )
    tag_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Optional per-tag weight; default 1.0",
    )


class OptimizationResult(BaseModel):
    """Outcome of pack optimization."""

    model_config = ConfigDict(extra="forbid")

    pack: TestPack
    selected_ids: list[str] = Field(default_factory=list)
    removed_as_redundant: int = Field(default=0, ge=0)
    mandatory_satisfied: list[MandatoryCategory] = Field(default_factory=list)
    mandatory_missing: list[MandatoryCategory] = Field(default_factory=list)
    tags_covered: list[str] = Field(default_factory=list)


class CoverageReport(BaseModel):
    """Multi-axis coverage after pack selection or execution."""

    model_config = ConfigDict(extra="forbid")

    axes: dict[str, float] = Field(
        default_factory=dict,
        description="Axis name → fraction of pool tags covered (0–1)",
    )
    covered_tags: list[str] = Field(default_factory=list)
    uncovered_tags: list[str] = Field(default_factory=list)
    critical_uncovered: list[str] = Field(
        default_factory=list,
        description="Mandatory categories or high-risk tags still uncovered",
    )
    executed_test_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SuiteManifest(BaseModel):
    """Frozen regression suite metadata on disk (DR-010)."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    version: int = Field(ge=1)
    requirements_fingerprint: str
    created_at: str
    endpoint_profile: str = Field(default="", description="URL pattern without secrets")
