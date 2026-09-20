"""Core domain models for AgentEval: trajectories, steps, tools, states, and scorecards."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Verdict(StrEnum):
    """The four explicit verdicts produced by the assurance engine."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIABLE = "UNVERIFIABLE"
    ANOMALOUS = "ANOMALOUS"


class FailureClass(StrEnum):
    """Standardized 12-class failure taxonomy for production agents."""

    MODEL_FAILURE = "MODEL_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    STATE_FAILURE = "STATE_FAILURE"
    CONTEXT_FAILURE = "CONTEXT_FAILURE"
    AUTH_FAILURE = "AUTH_FAILURE"
    PERMISSION_FAILURE = "PERMISSION_FAILURE"
    CHECKPOINT_FAILURE = "CHECKPOINT_FAILURE"
    IDEMPOTENCY_FAILURE = "IDEMPOTENCY_FAILURE"
    GUARDRAIL_FAILURE = "GUARDRAIL_FAILURE"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    EXTERNAL_SYSTEM_FAILURE = "EXTERNAL_SYSTEM_FAILURE"


class ToolCall(BaseModel):
    """Represents an agent's request to execute an external tool."""

    model_config = ConfigDict(extra="forbid")

    call_id: str = Field(description="Unique identifier for this invocation")
    tool_name: str = Field(description="Name of the target tool")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool invocation parameters")
    idempotency_key: str | None = Field(default=None, description="Idempotency key for safe retries")
    timestamp_ns: int = Field(default=0, description="Invocation timestamp in nanoseconds")


class ToolResult(BaseModel):
    """Represents the execution outcome of an invoked tool."""

    model_config = ConfigDict(extra="forbid")

    call_id: str = Field(description="Matches the corresponding ToolCall call_id")
    tool_name: str = Field(description="Name of the executed tool")
    output: Any = Field(default=None, description="Raw return payload from the tool")
    is_error: bool = Field(default=False, description="True if tool failed or raised an exception")
    error_message: str | None = Field(default=None, description="Descriptive error string if is_error=True")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Execution wall-clock latency in milliseconds")
    mutated_state: bool = Field(default=False, description="True if tool caused persistent environment side effects")


class StepRecord(BaseModel):
    """Represents a single turn or iteration in an agent's reasoning-action loop."""

    model_config = ConfigDict(extra="forbid")

    step_number: int = Field(ge=1, description="1-indexed sequence number of the step")
    thought: str | None = Field(default=None, description="Optional reasoning explanation or summary")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tools called during this step")
    tool_results: list[ToolResult] = Field(default_factory=list, description="Results from tools executed in this step")
    state_snapshot_id: str | None = Field(default=None, description="Snapshot ID of environment after this step")
    tokens_used: int = Field(default=0, ge=0, description="Tokens consumed during this step")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Duration of this step in milliseconds")


class StateSnapshot(BaseModel):
    """Immutable hash fingerprint of environment state at a given point in time."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(description="Unique identifier for the snapshot")
    timestamp_ns: int = Field(description="Timestamp when snapshot was captured")
    file_hashes: dict[str, str] = Field(default_factory=dict, description="Relative path to SHA256 file hash")
    db_hashes: dict[str, str] = Field(default_factory=dict, description="Table name to hash of contents")
    custom_state: dict[str, Any] = Field(default_factory=dict, description="Arbitrary custom state attributes")


class StateDiff(BaseModel):
    """Deterministic diff between two environment state snapshots (Delta S)."""

    model_config = ConfigDict(extra="forbid")

    pre_snapshot_id: str = Field(description="Snapshot ID before execution")
    post_snapshot_id: str = Field(description="Snapshot ID after execution")
    files_added: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    files_deleted: list[str] = Field(default_factory=list)
    db_mutations: list[dict[str, Any]] = Field(default_factory=list)


class AgentLoopMetrics(BaseModel):
    """Performance and efficiency metrics captured from the agent execution loop."""

    model_config = ConfigDict(extra="forbid")

    agent_loop_iterations: int = Field(default=0, ge=0, description="Total turns executed in the loop")
    duplicate_actions: int = Field(default=0, ge=0, description="Identical consecutive tool calls detected")
    termination_reason: str = Field(default="COMPLETED", description="COMPLETED, MAX_STEPS, CRASH, or ABORTED")
    time_to_completion_ms: float = Field(default=0.0, ge=0.0, description="Total execution wall-clock time")
    tokens_consumed: int = Field(default=0, ge=0, description="Total tokens consumed across all steps")
    total_cost_usd: float = Field(default=0.0, ge=0.0, description="Calculated inference and tool cost")


class ExecutionTrace(BaseModel):
    """Complete, sealed trajectory log of an agent scenario execution."""

    model_config = ConfigDict(extra="forbid")

    execution_id: str = Field(description="Unique identifier for this evaluation run")
    scenario_id: str = Field(description="Identifier of the executed test scenario")
    agent_id: str = Field(description="Identifier and version of the agent under test")
    steps: list[StepRecord] = Field(default_factory=list, description="Ordered sequence of trajectory steps")
    state_snapshots: list[StateSnapshot] = Field(default_factory=list, description="Captured environment snapshots")
    state_diffs: list[StateDiff] = Field(default_factory=list, description="Computed pre/post state diffs")
    loop_metrics: AgentLoopMetrics = Field(default_factory=AgentLoopMetrics)
    verdict: Verdict = Field(default=Verdict.UNVERIFIABLE, description="Aggregated test verdict")
    failure_classes: list[FailureClass] = Field(default_factory=list, description="Specific failure categories identified")


class ReliabilityScorecard(BaseModel):
    """Multi-dimensional scorecard summarizing reliability across all planes."""

    model_config = ConfigDict(extra="forbid")

    outcome_pass: bool = Field(description="True if functional objective was met")
    trajectory_score: float = Field(ge=0.0, le=1.0, description="1.0 = shortest, non-looping path")
    recovery_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Success rate recovering from injected faults")
    idempotency_score: float = Field(default=1.0, ge=0.0, le=1.0, description="1.0 = zero duplicate side effects")
    duplicate_side_effects: int = Field(default=0, ge=0, description="Count of duplicate irreversible mutations")
    verdict: Verdict = Field(default=Verdict.UNVERIFIABLE)
    metrics: AgentLoopMetrics = Field(default_factory=AgentLoopMetrics)
    failure_classes: list[FailureClass] = Field(default_factory=list)
