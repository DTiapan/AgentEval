"""Frozen suite preview, init, and run — same logic as CLI, UI/API-ready."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentCard
from agenteval.db.config import database_path, use_sqlite_persistence
from agenteval.db.suite_repository import SuiteRepository
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
    TestPack,
)
from agenteval.planning.optimizer import TestPackOptimizer
from agenteval.planning.run_diff import diff_suite_runs
from agenteval.planning.suite_store import SuiteExistsError, SuiteStore
from agenteval.planning.suite_sync import SuiteSynchronizer, SuiteSyncResult
from agenteval.services.requirement_run_status import AssuranceSignoffContext


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
    """Orchestrate black-box suite operations without Typer/Rich."""

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
        self._use_sqlite = use_sqlite if use_sqlite is not None else use_sqlite_persistence()
        self._db_path = Path(db_path) if db_path is not None else None
        self._repo: SuiteRepository | None = None

    def _store(self) -> SuiteStore:
        return SuiteStore(self.suite_root)

    def _repository(self) -> SuiteRepository | None:
        if not self._use_sqlite:
            return None
        if self._repo is None:
            self._repo = SuiteRepository(self._db_path)
        return self._repo

    def _sqlite_primary(self) -> bool:
        return self._use_sqlite

    def _list_agent_ids(self, store: SuiteStore) -> list[str]:
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            return repo.list_agent_ids()
        return store.list_agent_ids()

    def _load_manifest(self, store: SuiteStore, agent_id: str) -> SuiteManifest:
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            return repo.load_manifest(agent_id)
        return store.load_manifest(agent_id)

    def _load_pack(self, store: SuiteStore, agent_id: str) -> TestPack:
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            return repo.load_pack(agent_id)
        return store.load_pack(agent_id)

    def _load_pool(self, store: SuiteStore, agent_id: str) -> list[CandidateTest]:
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            return repo.load_pool(agent_id)
        return store.load_pool(agent_id)

    def _load_requirements_text(self, store: SuiteStore, agent_id: str) -> str:
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            return repo.load_requirements_text(agent_id)
        path = store.agent_dir(agent_id) / "requirements.md"
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return ""

    def _load_latest_run(self, store: SuiteStore, agent_id: str) -> SuiteRunReport | None:
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            return repo.load_latest_run(agent_id)
        return store.load_latest_run(agent_id)

    def _load_requirements_result(self, agent_id: str) -> SuiteRequirementsResult | None:
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            try:
                return repo.load_requirements_result(agent_id)
            except FileNotFoundError:
                return None
        return None

    def get_requirements(self, agent_id: str) -> SuiteRequirementsResult:
        store = self._store()
        self._load_manifest(store, agent_id)
        result = self._load_requirements_result(agent_id)
        if result is None:
            manifest = self._load_manifest(store, agent_id)
            return SuiteRequirementsResult(
                agent_id=agent_id,
                suite_version=manifest.version,
                requirements=[],
            )
        return result

    def _load_run(self, store: SuiteStore, agent_id: str, run_id: str) -> SuiteRunReport | None:
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            return repo.load_run(agent_id, run_id)
        return store.load_run(agent_id, run_id)

    def _save_run(
        self,
        store: SuiteStore,
        agent_id: str,
        report: SuiteRunReport,
        *,
        endpoint_url: str,
    ) -> None:
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            repo.save_run(agent_id, report, endpoint_url=endpoint_url)
            return
        store.save_run(agent_id, report)

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
        """Persist frozen suite to SQLite when persistence is enabled."""
        repo = self._repository()
        if repo is not None:
            repo.init_suite(
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

        store = self._store()
        manifest = SuiteStore.new_manifest(card.id, fingerprint, endpoint_url or "")
        repo = self._repository()
        if self._sqlite_primary() and repo is not None:
            try:
                repo.init_suite(
                    manifest,
                    pool,
                    pack,
                    force=force_new_version,
                    agent_card_json=card.model_dump_json(),
                    requirements_text=prd_text,
                    enabled_domain_packs=enabled_domain_packs,
                )
            except SuiteExistsError:
                raise
            suite_path = str(self._db_path or database_path())
        else:
            try:
                out = store.init_suite(manifest, pool, pack, force=force_new_version)
            except SuiteExistsError:
                raise
            derived = out / "derived_agent_card.json"
            derived.write_text(card.model_dump_json(indent=2), encoding="utf-8")
            (out / "requirements.md").write_text(prd_text, encoding="utf-8")
            if probe is not None:
                (out / "endpoint_probe.json").write_text(
                    probe.model_dump_json(indent=2), encoding="utf-8"
                )
            suite_path = str(out)

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
        endpoint_url: str | None = None,
        audit_log_db_path: str | None = None,
        judge_mode: str = "hybrid",
        force_offline_judge: bool | None = None,
    ) -> SuiteRunReport:
        store = self._store()
        manifest = self._load_manifest(store, agent_id)
        pack = self._load_pack(store, agent_id)

        set_run_audit_log_db_path(audit_log_db_path)
        url = endpoint_url or manifest.endpoint_profile
        if not url:
            raise ValueError("endpoint_url required when suite has no stored endpoint")

        previous_run = self._load_latest_run(store, agent_id)
        runner = BlackboxRunner(
            endpoint_url=url,
            judge_mode=judge_mode,
            force_offline_judge=force_offline_judge,
        )
        report = runner.run_pack(pack)
        pool = self._load_pool(store, agent_id)
        coverage = CoverageMapper().report(pool, pack.tests)
        report.coverage_report = coverage

        if previous_run is not None:
            run_diff = diff_suite_runs(previous_run, report)
            if run_diff is not None:
                report.run_diff = run_diff.model_dump(mode="json")

        self._save_run(store, agent_id, report, endpoint_url=url)
        repo = self._repository()
        if repo is not None:
            return repo.enrich_run_report(report)
        return report

    def latest_run(self, agent_id: str) -> SuiteRunReport | None:
        return self._load_latest_run(self._store(), agent_id)

    def list_suites(self) -> list[SuiteListItem]:
        store = self._store()
        items: list[SuiteListItem] = []
        for agent_id in self._list_agent_ids(store):
            manifest = self._load_manifest(store, agent_id)
            pack = self._load_pack(store, agent_id)
            pool = self._load_pool(store, agent_id)
            items.append(
                SuiteListItem(
                    agent_id=agent_id,
                    suite_version=manifest.version,
                    requirements_fingerprint=manifest.requirements_fingerprint,
                    endpoint_profile=manifest.endpoint_profile,
                    pack_size=len(pack.tests),
                    pool_size=len(pool),
                    has_latest_run=self._load_latest_run(store, agent_id) is not None,
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
        store = self._store()
        manifest = self._load_manifest(store, agent_id)
        pack = self._load_pack(store, agent_id)
        pool = self._load_pool(store, agent_id)

        report = (
            self._load_run(store, agent_id, run_id)
            if run_id
            else self._load_latest_run(store, agent_id)
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
        if self._sqlite_primary() and repo is not None:
            card_json = repo.load_agent_card_json(agent_id)
            repo.apply_sync(
                updated_manifest,
                pool,
                new_pack,
                requirements_text=self._load_requirements_text(store, agent_id),
                agent_card_json=card_json,
            )
        else:
            store.apply_gap_extend(agent_id, updated_manifest, pool, new_pack, changelog)
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
        store = self._store()
        old_manifest = self._load_manifest(store, agent_id)
        old_pack = self._load_pack(store, agent_id)
        old_pool = self._load_pool(store, agent_id)

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
        if self._sqlite_primary() and repo is not None:
            repo.apply_sync(
                outcome.manifest,
                outcome.pool,
                outcome.pack,
                requirements_text=prd_text,
                agent_card_json=card.model_dump_json(),
                enabled_domain_packs=enabled_domain_packs,
            )
        else:
            store.apply_sync(
                agent_id,
                outcome.manifest,
                outcome.pool,
                outcome.pack,
                outcome.changelog,
            )
            derived = store.agent_dir(agent_id) / "derived_agent_card.json"
            derived.write_text(card.model_dump_json(indent=2), encoding="utf-8")
            (store.agent_dir(agent_id) / "requirements.md").write_text(prd_text, encoding="utf-8")
        return outcome.result

    def get_suite(self, agent_id: str) -> SuiteDetailResult:
        store = self._store()
        manifest = self._load_manifest(store, agent_id)
        pack = self._load_pack(store, agent_id)
        pool = self._load_pool(store, agent_id)
        coverage = CoverageMapper().report(pool, pack.tests)
        return SuiteDetailResult(
            manifest=manifest,
            optimized_pack=pack,
            candidate_pool_size=len(pool),
            requirements_text=self._load_requirements_text(store, agent_id),
            coverage=coverage,
            latest_run=self._load_latest_run(store, agent_id),
            requirements=self._load_requirements_result(agent_id),
        )

    def generate_html_report(
        self,
        agent_id: str,
        run_id: str | None = None,
        *,
        embed: bool = False,
        theme: str = "auto",
    ) -> str:
        store = self._store()
        manifest = self._load_manifest(store, agent_id)
        pack = self._load_pack(store, agent_id)
        report = (
            self._load_run(store, agent_id, run_id)
            if run_id
            else self._load_latest_run(store, agent_id)
        )
        if report is None:
            target = f"run '{run_id}'" if run_id else "latest run"
            raise FileNotFoundError(f"No execution {target} found for agent '{agent_id}'")
        from agenteval.reporting.html_report import HTMLReportGenerator

        signoff: AssuranceSignoffContext | None = None
        repo = self._repository()
        if repo is not None:
            signoff = repo.load_signoff_context(agent_id, report.suite_version, report.run_id)

        return HTMLReportGenerator.generate(
            report,
            pack,
            manifest=manifest,
            embed=embed,
            theme=theme,
            signoff=signoff,
        )
