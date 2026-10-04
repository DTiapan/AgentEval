"""Request bodies for the HTTP API (responses reuse planning/core Pydantic models)."""

from pydantic import BaseModel, ConfigDict, Field

from agenteval.targets import TargetConnectionProfile


class PrdBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements_text: str = Field(min_length=1, description="Functional requirements markdown")
    agent_id: str = Field(min_length=1, max_length=128)
    endpoint_url: str | None = None
    probe_endpoint: bool = True
    max_tests: int = Field(default=10, ge=1, le=500)
    target_tier: str | None = Field(default=None, description="P0, P1, P2, or None for all")
    selected_test_ids: list[str] | None = Field(
        default=None, description="Explicit test IDs selected by user"
    )
    suite_root: str = ".agenteval/suites"
    headers: dict[str, str] = Field(
        default_factory=dict, description="Custom HTTP headers to send with probe"
    )
    auth_profile: TargetConnectionProfile | None = Field(
        default=None, description="Target connection auth profile"
    )


class SuiteInitRequest(PrdBootstrapRequest):
    model_config = ConfigDict(extra="forbid")

    force_new_version: bool = False
    enabled_domain_packs: list[str] = Field(default_factory=list)


class EndpointProbeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint_url: str = Field(
        min_length=1, description="Agent HTTP URL to POST (server-side probe)"
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="Custom HTTP headers to send with probe"
    )
    auth_profile: TargetConnectionProfile | None = Field(
        default=None, description="Target connection auth profile"
    )


class SuiteRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint_url: str | None = None
    audit_log_db_path: str | None = None
    suite_root: str = ".agenteval/suites"
    judge_mode: str = Field(
        default="hybrid",
        description="Evaluation strategy: 'hybrid' (deterministic + LLM judge fallback), 'deterministic_only', or 'llm_judge'",
    )
    max_concurrency: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Maximum parallel test executions within a run (default: 8)",
    )
    wait: bool = Field(
        default=False,
        description="Whether to block synchronously until the run finishes (default: False)",
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="Custom HTTP headers to forward to agent"
    )
    auth_profile: TargetConnectionProfile | None = Field(
        default=None, description="Target connection auth profile"
    )


class RunProgressSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completed: int = 0
    total: int = 0
    percent: float = 0.0


class RunJobStatusSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    agent_id: str
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    progress: RunProgressSchema = Field(default_factory=RunProgressSchema)
    error: str | None = None


class SuiteGapExtendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_add: int = Field(default=5, ge=1, le=25)
    run_id: str | None = None
    suite_root: str = ".agenteval/suites"


class SuiteSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements_text: str = Field(min_length=1, description="Updated functional requirements")
    endpoint_url: str | None = None
    probe_endpoint: bool = False
    max_tests: int = Field(default=10, ge=1, le=500)
    target_tier: str | None = Field(default=None, description="P0, P1, P2, or None for all")
    selected_test_ids: list[str] | None = Field(
        default=None, description="Explicit test IDs selected by user"
    )
    suite_root: str = ".agenteval/suites"
    enabled_domain_packs: list[str] = Field(default_factory=list)
