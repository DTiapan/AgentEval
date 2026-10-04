"""Frozen suite preview, init, and run — same logic as CLI, UI/API-ready."""

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentCard
from agenteval.db.config import database_path
from agenteval.db.protocol import SuiteRepositoryProtocol
from agenteval.db.suite_repository import create_suite_repository
from agenteval.ingest.bootstrap import AgentBootstrap
from agenteval.ingest.endpoint_probe import EndpointProbeResult
from agenteval.packs.enabled import set_run_audit_log_db_path
from agenteval.packs.registry import discover_domain_packs
from agenteval.planning.blackbox_runner import BlackboxRunner
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.coverage import CoverageMapper
from agenteval.planning.gap_loop import SuiteGapExtender
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator
from agenteval.planning.models import (
    BudgetProjection,
    CandidateTest,
    CoverageReport,
    DomainPackListResult,
    DomainPackSummary,
    PriorityTier,
    SuiteGapLoopResult,
    SuiteManifest,
    SuiteRequirementsResult,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.planning.optimizer import TestPackOptimizer
from agenteval.planning.run_diff import diff_suite_runs
from agenteval.planning.suite_store import SuiteStore
from agenteval.planning.suite_sync import SuiteSynchronizer, SuiteSyncResult
from agenteval.telemetry import start_span


class SuitePreviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_card: AgentCard
    requirements_fingerprint: str
    candidate_pool: list[CandidateTest]
    optimized_pack: TestPack
    coverage: CoverageReport
    endpoint_probe: EndpointProbeResult | None = None
    marginal_curve: list[BudgetProjection] = Field(default_factory=list)


class SuiteListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    suite_version: int
    requirements_fingerprint: str
    endpoint_profile: str
    pack_size: int
    pool_size: int
    has_latest_run: bool


class SuiteDetailResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: SuiteManifest
    optimized_pack: TestPack
    candidate_pool_size: int
    requirements_text: str = ""
    coverage: CoverageReport | None = None
    latest_run: SuiteRunReport | None = None
    requirements: SuiteRequirementsResult | None = None


class SuiteInitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite_path: str
    agent_id: str
    requirements_fingerprint: str
    candidate_pool_size: int
    optimized_pack_size: int
    coverage: CoverageReport
    endpoint_stored: bool
    agent_card: AgentCard
    endpoint_probe: EndpointProbeResult | None = None


class SuiteWorkflow:
    """Orchestrate black-box suite operations without Typer/Rich (backed by SQLite)."""

    def __init__(
        self,
        suite_root: Path | str = ".agenteval/suites",
        max_tests: int = 10,
        *,
        use_sqlite: bool | None = None,
        db_path: Path | str | None = None,
    ) -> None:
        self.suite_root = Path(suite_root)
        self.max_tests = max_tests
        self._db_path = Path(db_path) if db_path is not None else None
        self._repo: SuiteRepositoryProtocol | None = None

    def _repository(self) -> SuiteRepositoryProtocol:
        if self._repo is None:
            self._repo = create_suite_repository(self._db_path)
        return self._repo

    def _list_agent_ids(self) -> list[str]:
        return self._repository().list_agent_ids()

    def _load_manifest(self, agent_id: str) -> SuiteManifest:
        return self._repository().load_manifest(agent_id)

    def _load_pack(self, agent_id: str) -> TestPack:
        return self._repository().load_pack(agent_id)

    def _load_pool(self, agent_id: str) -> list[CandidateTest]:
        return self._repository().load_pool(agent_id)

    def _load_requirements_text(self, agent_id: str) -> str:
        return self._repository().load_requirements_text(agent_id)

    def _load_latest_run(self, agent_id: str) -> SuiteRunReport | None:
        return self._repository().load_latest_run(agent_id)

    def _load_requirements_result(self, agent_id: str) -> SuiteRequirementsResult | None:
        try:
            return self._repository().load_requirements_result(agent_id)
        except FileNotFoundError:
            return None

    def get_requirements(self, agent_id: str) -> SuiteRequirementsResult:
        manifest = self._load_manifest(agent_id)
        result = self._load_requirements_result(agent_id)
        if result is None:
            return SuiteRequirementsResult(
                agent_id=agent_id,
                suite_version=manifest.version,
                requirements=[],
            )
        return result

    def _load_run(self, agent_id: str, run_id: str) -> SuiteRunReport | None:
        return self._repository().load_run(agent_id, run_id)

    def _save_run(
        self,
        agent_id: str,
        report: SuiteRunReport,
        *,
        endpoint_url: str,
    ) -> None:
        self._repository().finalize_run(agent_id, report, endpoint_url=endpoint_url)

    def list_domain_packs(self) -> DomainPackListResult:
        summaries: list[DomainPackSummary] = []
        for pack_id, pack in sorted(discover_domain_packs().items()):
            manifest = pack.manifest
            summaries.append(
                DomainPackSummary(
                    id=pack_id,
                    name=manifest.name,
                    version=manifest.version,
                    display_name=manifest.display_name,
                    description=manifest.description,
                    slots_filled=manifest.slots_filled,
                )
            )
        return DomainPackListResult(packs=summaries)

    def write_init_to_sqlite(
        self,
        manifest: SuiteManifest,
        pool: list[CandidateTest],
        pack: TestPack,
        *,
        force: bool = False,
        agent_card_json: str | None = None,
        requirements_text: str = "",
        enabled_domain_packs: list[str] | None = None,
    ) -> None:
        """Persist frozen suite to SQLite."""
        self._repository().init_suite(
            manifest,
            pool,
            pack,
            force=force,
            agent_card_json=agent_card_json,
            requirements_text=requirements_text,
            enabled_domain_packs=enabled_domain_packs,
        )

    def preview_from_prd_text(
        self,
        prd_text: str,
        *,
        agent_id: str,
        endpoint_url: str | None = None,
        probe_endpoint: bool = True,
        max_tier: PriorityTier | None = None,
        selected_test_ids: list[str] | None = None,
    ) -> SuitePreviewResult:
        with start_span(
            "suite.preview",
            attributes={
                "agenteval.agent_id": agent_id,
                "agenteval.has_endpoint": bool(endpoint_url),
            },
        ):
            card, fingerprint, probe = AgentBootstrap.from_text(
                prd_text,
                agent_id=agent_id,
                endpoint_url=endpoint_url,
                probe_endpoint=probe_endpoint and endpoint_url is not None,
            )
            pool, pack, coverage = SuiteBootstrap(max_tests=self.max_tests).build(
                card,
                fingerprint,
                max_tier=max_tier,
                selected_test_ids=selected_test_ids,
            )
            hyp_gen = FailureHypothesisGenerator()
            applicable = hyp_gen.infer_applicable_mandatory(card.capabilities)
            marginal_curve = TestPackOptimizer.compute_marginal_coverage_curve(pool, applicable)
            return SuitePreviewResult(
                agent_card=card,
                requirements_fingerprint=fingerprint,
                candidate_pool=pool,
                optimized_pack=pack,
                coverage=coverage,
                endpoint_probe=probe,
                marginal_curve=marginal_curve,
            )

    def init_from_prd_text(
        self,
        prd_text: str,
        *,
        agent_id: str,
        endpoint_url: str | None = None,
        probe_endpoint: bool = True,
        force_new_version: bool = False,
        enabled_domain_packs: list[str] | None = None,
        max_tier: PriorityTier | None = None,
        selected_test_ids: list[str] | None = None,
    ) -> SuiteInitResult:
        with start_span(
            "suite.init",
            attributes={
                "agenteval.agent_id": agent_id,
                "agenteval.has_endpoint": bool(endpoint_url),
                "agenteval.force_new_version": force_new_version,
            },
        ):
            card, fingerprint, probe = AgentBootstrap.from_text(
                prd_text,
                agent_id=agent_id,
                endpoint_url=endpoint_url,
                probe_endpoint=probe_endpoint and endpoint_url is not None,
            )
            pool, pack, coverage = SuiteBootstrap(max_tests=self.max_tests).build(
                card,
                fingerprint,
                max_tier=max_tier,
                selected_test_ids=selected_test_ids,
            )

            manifest = SuiteStore.new_manifest(card.id, fingerprint, endpoint_url or "")
            repo = self._repository()
            repo.init_suite(
                manifest,
                pool,
                pack,
                force=force_new_version,
                agent_card_json=card.model_dump_json(),
                requirements_text=prd_text,
                enabled_domain_packs=enabled_domain_packs,
            )
            suite_path = str(self._db_path or database_path())

            return SuiteInitResult(
                suite_path=suite_path,
                agent_id=card.id,
                requirements_fingerprint=fingerprint,
                candidate_pool_size=len(pool),
                optimized_pack_size=len(pack.tests),
                coverage=coverage,
                endpoint_stored=bool(endpoint_url),
                agent_card=card,
                endpoint_probe=probe,
            )

    def run_suite(
        self,
        agent_id: str,
        *,
        run_id: str | None = None,
        endpoint_url: str | None = None,
        audit_log_db_path: str | None = None,
        judge_mode: str = "hybrid",
        force_offline_judge: bool | None = None,
        max_concurrency: int | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> SuiteRunReport:
        manifest = self._load_manifest(agent_id)
        pack = self._load_pack(agent_id)

        set_run_audit_log_db_path(audit_log_db_path)
        url = endpoint_url or manifest.endpoint_profile
        if not url:
            raise ValueError("endpoint_url required when suite has no stored endpoint")

        previous_run = self._load_latest_run(agent_id)
        effective_run_id = run_id or uuid4().hex[:12]
        repo = self._repository()
        repo.initialize_run(
            agent_id=agent_id,
            run_id=effective_run_id,
            suite_version=manifest.version,
            endpoint_url=url,
        )

        def _on_result(res: TestCaseResult) -> None:
            repo.save_partial_result(effective_run_id, res)

        runner = BlackboxRunner(
            endpoint_url=url,
            judge_mode=judge_mode,
            force_offline_judge=force_offline_judge,
            max_workers=max_concurrency,
        )

        try:
            report = runner.run_pack(
                pack,
                run_id=effective_run_id,
                max_workers=max_concurrency,
                on_progress=on_progress,
                on_result=_on_result,
            )
            pool = self._load_pool(agent_id)
            coverage = CoverageMapper().report(pool, pack.tests)
            report.coverage_report = coverage

            if previous_run is not None:
                run_diff = diff_suite_runs(previous_run, report)
                if run_diff is not None:
                    report.run_diff = run_diff.model_dump(mode="json")

            if report.run_id != effective_run_id:
                repo.delete_run(effective_run_id)

            self._save_run(agent_id, report, endpoint_url=url)
        except Exception as exc:
            repo.mark_run_failed(effective_run_id, str(exc))
            raise

        return repo.enrich_run_report(report)

    def latest_run(self, agent_id: str) -> SuiteRunReport | None:
        report = self._load_latest_run(agent_id)
        if report is None:
            return None
        return self._repository().enrich_run_report(report)

    def get_run(self, agent_id: str, run_id: str) -> SuiteRunReport | None:
        """Load a specific run report by agent_id and run_id, enriched with signoff."""
        report = self._load_run(agent_id, run_id)
        if report is None:
            return None
        return self._repository().enrich_run_report(report)

    def list_suites(self) -> list[SuiteListItem]:
        items: list[SuiteListItem] = []
        for agent_id in self._list_agent_ids():
            manifest = self._load_manifest(agent_id)
            pack = self._load_pack(agent_id)
            pool = self._load_pool(agent_id)
            items.append(
                SuiteListItem(
                    agent_id=agent_id,
                    suite_version=manifest.version,
                    requirements_fingerprint=manifest.requirements_fingerprint,
                    endpoint_profile=manifest.endpoint_profile,
                    pack_size=len(pack.tests),
                    pool_size=len(pool),
                    has_latest_run=self._load_latest_run(agent_id) is not None,
                )
            )
        return items

    def extend_gaps_from_latest_run(
        self,
        agent_id: str,
        *,
        max_add: int = 5,
        run_id: str | None = None,
    ) -> SuiteGapLoopResult:
        with start_span(
            "suite.extend_gaps",
            attributes={
                "agenteval.agent_id": agent_id,
                "agenteval.run_id": run_id or "",
                "agenteval.max_add": max_add,
            },
        ):
            manifest = self._load_manifest(agent_id)
            pack = self._load_pack(agent_id)
            pool = self._load_pool(agent_id)

            report = (
                self._load_run(agent_id, run_id)
                if run_id
                else self._load_latest_run(agent_id)
            )
            if report is None:
                raise FileNotFoundError(
                    f"No assurance run for agent '{agent_id}'. Run the suite before extending gaps."
                )

            executed_ids = {r.test_id for r in report.results}
            executed_tests = [t for t in pack.tests if t.id in executed_ids]
            if not executed_tests:
                raise ValueError("Latest run has no overlapping tests with the frozen pack.")

            extender = SuiteGapExtender()
            pack_ceiling = len(pack.tests) + max_add
            result, changelog, new_pack = extender.extend(
                agent_id=agent_id,
                manifest=manifest,
                pool=pool,
                pack=pack,
                executed_tests=executed_tests,
                triggered_by_run_id=report.run_id,
                max_pack_tests=pack_ceiling,
                max_add=max_add,
            )
            if changelog is None or new_pack is None:
                return result

            updated_manifest = SuiteManifest(
                agent_id=manifest.agent_id,
                version=result.new_version,
                requirements_fingerprint=manifest.requirements_fingerprint,
                created_at=manifest.created_at,
                endpoint_profile=manifest.endpoint_profile,
            )
            repo = self._repository()
            card_json = repo.load_agent_card_json(agent_id)
            repo.apply_sync(
                updated_manifest,
                pool,
                new_pack,
                requirements_text=self._load_requirements_text(agent_id),
                agent_card_json=card_json,
            )
            return result

    def sync_from_prd_text(
        self,
        agent_id: str,
        prd_text: str,
        *,
        endpoint_url: str | None = None,
        probe_endpoint: bool = False,
        enabled_domain_packs: list[str] | None = None,
    ) -> SuiteSyncResult:
        with start_span(
            "suite.sync",
            attributes={
                "agenteval.agent_id": agent_id,
                "agenteval.has_endpoint": bool(endpoint_url),
            },
        ):
            old_manifest = self._load_manifest(agent_id)
            old_pack = self._load_pack(agent_id)
            old_pool = self._load_pool(agent_id)

            card, fingerprint, _probe = AgentBootstrap.from_text(
                prd_text,
                agent_id=agent_id,
                endpoint_url=endpoint_url or old_manifest.endpoint_profile or None,
                probe_endpoint=probe_endpoint and endpoint_url is not None,
            )
            profile = endpoint_url if endpoint_url is not None else old_manifest.endpoint_profile
            outcome = SuiteSynchronizer(max_tests=self.max_tests).compute_sync(
                agent_id=agent_id,
                card=card,
                new_fingerprint=fingerprint,
                old_manifest=old_manifest,
                old_pool=old_pool,
                old_pack=old_pack,
                endpoint_profile=profile,
            )
            if (
                outcome.changelog is None
                or outcome.manifest is None
                or outcome.pool is None
                or outcome.pack is None
            ):
                return outcome.result

            repo = self._repository()
            repo.apply_sync(
                outcome.manifest,
                outcome.pool,
                outcome.pack,
                requirements_text=prd_text,
                agent_card_json=card.model_dump_json(),
                enabled_domain_packs=enabled_domain_packs,
            )
            return outcome.result

    def get_suite(self, agent_id: str) -> SuiteDetailResult:
        manifest = self._load_manifest(agent_id)
        pack = self._load_pack(agent_id)
        pool = self._load_pool(agent_id)
        coverage = CoverageMapper().report(pool, pack.tests)
        return SuiteDetailResult(
            manifest=manifest,
            optimized_pack=pack,
            candidate_pool_size=len(pool),
            requirements_text=self._load_requirements_text(agent_id),
            coverage=coverage,
            latest_run=self._load_latest_run(agent_id),
            requirements=self._load_requirements_result(agent_id),
        )

    def delete_suite(self, agent_id: str) -> bool:
        """Permanently delete an agent suite, versions, and runs from database."""
        deleted = self._repository().delete_agent(agent_id)
        if not deleted:
            raise FileNotFoundError(f"No suite found for agent '{agent_id}'.")
        return True

    def generate_html_report(
        self,
        agent_id: str,
        run_id: str | None = None,
        *,
        embed: bool = False,
        theme: str = "auto",
    ) -> str:
        manifest = self._load_manifest(agent_id)
        pack = self._load_pack(agent_id)
        report = (
            self._load_run(agent_id, run_id)
            if run_id
            else self._load_latest_run(agent_id)
        )
        if report is None:
            target = f"run '{run_id}'" if run_id else "latest run"
            raise FileNotFoundError(f"No execution {target} found for agent '{agent_id}'")
        from agenteval.reporting.html_report import HTMLReportGenerator

        repo = self._repository()
        signoff = repo.load_signoff_context(agent_id, report.suite_version, report.run_id)

        return HTMLReportGenerator.generate(
            report,
            pack,
            manifest=manifest,
            embed=embed,
            theme=theme,
            signoff=signoff,
        )
