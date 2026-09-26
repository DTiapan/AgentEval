"""Request bodies for the HTTP API (responses reuse planning/core Pydantic models)."""

from pydantic import BaseModel, ConfigDict, Field


class PrdBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements_text: str = Field(min_length=1, description="Functional requirements markdown")
    agent_id: str = Field(min_length=1, max_length=128)
    endpoint_url: str | None = None
    probe_endpoint: bool = True
    max_tests: int = Field(default=10, ge=1, le=50)
    suite_root: str = ".agenteval/suites"


class SuiteInitRequest(PrdBootstrapRequest):
    model_config = ConfigDict(extra="forbid")

    force_new_version: bool = False


class EndpointProbeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint_url: str = Field(min_length=1, description="Agent HTTP URL to POST (server-side probe)")


class SuiteRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint_url: str | None = None
    suite_root: str = ".agenteval/suites"


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
    max_tests: int = Field(default=10, ge=1, le=50)
    suite_root: str = ".agenteval/suites"
