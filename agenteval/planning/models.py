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


class PriorityTier(StrEnum):
    """Execution priority tier for test candidates and packs (human-in-the-loop curation)."""

    P0_CRITICAL = "P0"
    P1_RECOMMENDED = "P1"
    P2_EXTENDED = "P2"


class BudgetProjection(BaseModel):
    """Projected coverage and cost for a given priority tier or test count."""

    model_config = ConfigDict(extra="forbid")

    tier: PriorityTier
    label: str = Field(description="Short human label: Smoke (P0), Standard (P0+P1), Full Audit (All)")
    target_test_count: int = Field(ge=0, description="Recommended number of tests")
    projected_coverage_pct: float = Field(ge=0.0, le=100.0, description="Projected requirement coverage %")
    estimated_latency_ms: float = Field(ge=0.0, description="Estimated total execution latency in ms")
    estimated_cost_usd: float = Field(ge=0.0, description="Estimated LLM/token cost in USD")
    mandatory_floors_covered: int = Field(ge=0)
    mandatory_floors_total: int = Field(ge=0)


class FailureHypothesis(BaseModel):
    """Rule-generated failure mode for a single capability (B1 output)."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    capability_id: str
    category: str
    failure_mode: str
    coverage_tags: list[str] = Field(default_factory=list)
    mandatory_categories: list[MandatoryCategory] = Field(default_factory=list)
    expected_behavior: str
    task_prompt: str = Field(
        description="Capability-specific user message body (persona framing applied in B2)"
    )
    provenance: ProvenanceLayer = Field(default=ProvenanceLayer.HYPOTHESIZED)


class CandidateQualityScore(BaseModel):
    """Multi-axis quality grading for a candidate test."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    severity: float = Field(ge=0.0, le=1.0, description="Failure severity weight (0-1)")
    novelty: float = Field(ge=0.0, le=1.0, description="Uniqueness vs accepted pool (0-1)")
    flakiness_risk: float = Field(ge=0.0, le=1.0, description="Likelihood of flake or ambiguity (0-1)")
    execution_cost: float = Field(ge=0.0, le=1.0, description="Normalized execution cost (0-1)")
    composite_score: float = Field(ge=0.0, le=1.0, description="Weighted composite quality (0-1)")
    recommended_tier: PriorityTier = Field(
        default=PriorityTier.P1_RECOMMENDED,
        description="Recommended priority tier from Jev",
    )
    source: str = Field(
        default="local_heuristic",
        description="Classifier origin (typesafe_jev, local_heuristic, local_heuristic_fallback)",
    )
    rationale: str = Field(default="", description="Reasoning for assigned quality grade")


class CandidateTest(BaseModel):
    """A single generated test candidate (pool member; not necessarily executed)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable test identifier")
    capability_id: str = Field(
        description="Declared capability this test exercises (for suite prune)"
    )
    persona_id: str = Field(description="Persona slug or identifier")
    name: str = Field(description="Short human-readable title")
    user_prompt: str = Field(description="Input sent to the agent endpoint")
    expected_behavior: str = Field(description="Observable expectation (no internal state claims)")
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
    execution_cost: float = Field(
        default=1.0, ge=0.01, description="Relative cost weight for optimizer"
    )
    is_mandatory: bool = Field(
        default=False,
        description="Always include in pack when present in pool",
    )
    priority_tier: PriorityTier = Field(
        default=PriorityTier.P1_RECOMMENDED,
        description="P0 (Critical floors), P1 (Core workflows), P2 (Adversarial fuzzing)",
    )
    quality_score: CandidateQualityScore | None = Field(
        default=None,
        description="Multi-axis Jev quality score (composite Q, severity, novelty, flakiness, rationale)",
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
    max_tier: PriorityTier | None = Field(
        default=None,
        description="If set, only consider candidates up to this tier (P0, P1, P2)",
    )
    selected_test_ids: list[str] | None = Field(
        default=None,
        description="Explicit candidate IDs chosen by user (overrides or seeds selection)",
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


class ObservationBundle(BaseModel):
    """Black-box observable capture for one test invocation (B7)."""

    model_config = ConfigDict(extra="forbid")

    test_id: str
    user_prompt: str
    response_text: str
    http_status: int = Field(default=200)
    latency_ms: float = Field(default=0.0)
    raw_json: dict[str, Any] = Field(default_factory=dict)


class ExecutionStep(BaseModel):
    """One sealed step in a black-box run (persisted with TestCaseResult)."""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    kind: str = Field(
        description="user_message | agent_thought | tool_call | http_response | invariant_check"
    )
    label: str
    thought: str = ""
    action_tool: str = ""
    action_args: dict[str, Any] = Field(default_factory=dict)
    observation: str = ""
    http_status: int | None = None
    latency_ms: float | None = None
    is_failure: bool = False


class TestCaseResult(BaseModel):
    """Rule-based outcome for one candidate test (no LLM judge)."""

    model_config = ConfigDict(extra="forbid")

    test_id: str
    verdict: str = Field(description="PASS | FAIL | UNVERIFIABLE")
    observation: ObservationBundle
    rationale: str = ""
    trajectory: list[ExecutionStep] = Field(
        default_factory=list,
        description="Sealed steps derived at run time from HTTP observation (not UI fiction).",
    )


class AcceptanceCriterionSummary(BaseModel):
    """Frozen acceptance criterion exposed via API (FR-B-03)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    stable_id: str
    description: str
    evidence_kind: str
    check_kind: str


class RequirementSummary(BaseModel):
    """Requirement with nested criteria for sign-off views."""

    model_config = ConfigDict(extra="forbid")

    stable_id: str
    statement: str
    source_kind: str
    review_status: str
    criteria: list[AcceptanceCriterionSummary] = Field(default_factory=list)


class DomainPackSummary(BaseModel):
    """Installed domain pack entry point (FR-P-06)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    version: str
    display_name: str
    description: str = ""
    slots_filled: list[str] = Field(default_factory=list)


class DomainPackListResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    packs: list[DomainPackSummary] = Field(default_factory=list)


class SuiteRequirementsResult(BaseModel):
    """Normalized requirements for a frozen suite version."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    suite_version: int
    requirements: list[RequirementSummary] = Field(default_factory=list)


class CriterionVerdictSummary(BaseModel):
    """Per-criterion verdict for one test execution (FR-B-14)."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    requirement_stable_id: str
    criterion_stable_id: str
    test_id: str
    verdict: str
    verdict_tier: str
    rationale: str
    evidence_item_ids: list[str] = Field(default_factory=list)


class SuiteRunReport(BaseModel):
    """Aggregated suite execution report."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    run_id: str
    suite_version: int
    results: list[TestCaseResult] = Field(default_factory=list)
    passed: int = 0
    failed: int = 0
    unverifiable: int = 0
    coverage_report: CoverageReport | None = None
    run_diff: dict[str, Any] | None = Field(
        default=None,
        description="Serialized SuiteRunDiff vs previous run on same suite version",
    )
    criterion_verdicts: list[CriterionVerdictSummary] = Field(
        default_factory=list,
        description="Populated when SQLite v2 verdict rows exist for this run",
    )


class SuiteManifest(BaseModel):
    """Frozen regression suite metadata on disk (DR-010)."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    version: int = Field(ge=1)
    requirements_fingerprint: str
    created_at: str
    endpoint_profile: str = Field(default="", description="URL pattern without secrets")


class SuiteSyncChangelog(BaseModel):
    """Recorded prune/extend event for audit (DR-011)."""

    model_config = ConfigDict(extra="forbid")

    suite_version: int
    timestamp: str
    requirements_fingerprint: str
    removed_capabilities: list[str] = Field(default_factory=list)
    added_capabilities: list[str] = Field(default_factory=list)
    removed_test_ids: list[str] = Field(default_factory=list)
    archived_tests: list[CandidateTest] = Field(default_factory=list)


class SuiteGapChangelog(BaseModel):
    """Recorded B5 gap-loop extend event (append-only pack growth)."""

    model_config = ConfigDict(extra="forbid")

    event: str = Field(default="gap_extend")
    suite_version: int
    timestamp: str
    triggered_by_run_id: str | None = None
    targeted_tags: list[str] = Field(default_factory=list)
    added_test_ids: list[str] = Field(default_factory=list)


class SuiteGapLoopResult(BaseModel):
    """Outcome of explicit gap-driven pack extension (never on plain suite run)."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    previous_version: int
    new_version: int
    triggered_by_run_id: str | None = None
    targeted_tags: list[str] = Field(default_factory=list)
    added_test_ids: list[str] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
    pack_size: int
    pool_size: int
    coverage_before: CoverageReport
    coverage_after: CoverageReport
    noop: bool = False
