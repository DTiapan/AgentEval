"""Protocol defining the repository contract for AgentEval suite persistence (ADR-007)."""

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from agenteval.services.requirement_run_status import AssuranceSignoffContext
    from agenteval.services.run_manager import RunJobInfo

from agenteval.domain.models import FrozenTestCaseRecord, RequirementRecord
from agenteval.planning.models import (
    CandidateTest,
    SuiteManifest,
    SuiteRequirementsResult,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)


@runtime_checkable
class SuiteRepositoryProtocol(Protocol):
    """Abstract persistence interface implemented by SQLite and PostgreSQL backends."""

    def close(self) -> None: ...

    def list_agent_ids(self) -> list[str]: ...

    def delete_agent(self, agent_id: str) -> bool: ...

    def init_suite(
        self,
        manifest: SuiteManifest,
        pool: list[CandidateTest],
        pack: TestPack,
        *,
        force: bool = False,
        agent_card_json: str | None = None,
        requirements_text: str = "",
        enabled_domain_packs: list[str] | None = None,
        connection_profile_json: str | None = None,
    ) -> None: ...

    def load_manifest(self, agent_id: str) -> SuiteManifest: ...

    def load_pack(self, agent_id: str) -> TestPack: ...

    def load_pool(self, agent_id: str) -> list[CandidateTest]: ...

    def load_requirements_text(self, agent_id: str) -> str: ...

    def load_agent_card_json(self, agent_id: str) -> str | None: ...

    def load_requirements_result(self, agent_id: str) -> SuiteRequirementsResult | None: ...

    def load_normalized_requirements(self, agent_id: str) -> list[RequirementRecord]: ...

    def load_normalized_test_cases(self, agent_id: str) -> list[FrozenTestCaseRecord]: ...

    def enrich_run_report(self, report: SuiteRunReport) -> SuiteRunReport: ...

    def load_signoff_context(
        self, agent_id: str, suite_version: int, run_id: str
    ) -> "AssuranceSignoffContext | None": ...

    def initialize_run(
        self,
        agent_id: str,
        run_id: str,
        suite_version: int,
        *,
        endpoint_url: str,
        connection_profile_json: str | None = None,
    ) -> str: ...

    def save_partial_result(
        self,
        run_id: str,
        result: TestCaseResult,
    ) -> None: ...

    def finalize_run(
        self,
        agent_id: str,
        report: SuiteRunReport,
        *,
        endpoint_url: str,
        connection_profile_json: str | None = None,
    ) -> None: ...

    def mark_run_failed(
        self,
        run_id: str,
        error_message: str,
    ) -> None: ...

    def delete_run(self, run_id: str) -> None: ...

    def load_run(
        self,
        agent_id: str,
        run_id: str,
    ) -> SuiteRunReport | None: ...

    def load_latest_run(self, agent_id: str) -> SuiteRunReport | None: ...

    def get_run_record(self, run_id: str) -> dict[str, Any] | None: ...

    def apply_sync(
        self,
        manifest: SuiteManifest,
        pool: list[CandidateTest],
        pack: TestPack,
        *,
        requirements_text: str = "",
        agent_card_json: str | None = None,
        enabled_domain_packs: list[str] | None = None,
    ) -> None: ...

    def ensure_default_target(self, agent_id: str, endpoint_url: str) -> str | None: ...

    def save_run_job(self, job: "RunJobInfo") -> None: ...

    def get_run_job(self, run_id: str) -> "RunJobInfo | None": ...
