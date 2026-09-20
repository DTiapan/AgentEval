"""Frozen suite preview, init, and run — same logic as CLI, UI/API-ready."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from agenteval.core.manifest import AgentCard
from agenteval.ingest.bootstrap import AgentBootstrap
from agenteval.ingest.endpoint_probe import EndpointProbeResult
from agenteval.planning.blackbox_runner import BlackboxRunner
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.coverage import CoverageMapper
from agenteval.planning.models import (
    CandidateTest,
    CoverageReport,
    SuiteRunReport,
    TestPack,
)
from agenteval.planning.run_diff import diff_suite_runs
from agenteval.planning.suite_store import SuiteExistsError, SuiteStore


class SuitePreviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_card: AgentCard
    requirements_fingerprint: str
    candidate_pool: list[CandidateTest]
    optimized_pack: TestPack
    coverage: CoverageReport
    endpoint_probe: EndpointProbeResult | None = None


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
    ) -> None:
        self.suite_root = Path(suite_root)
        self.max_tests = max_tests

    def preview_from_prd_text(
        self,
        prd_text: str,
        *,
        agent_id: str,
        endpoint_url: str | None = None,
        probe_endpoint: bool = True,
    ) -> SuitePreviewResult:
        card, fingerprint, probe = AgentBootstrap.from_text(
            prd_text,
            agent_id=agent_id,
            endpoint_url=endpoint_url,
            probe_endpoint=probe_endpoint and endpoint_url is not None,
        )
        pool, pack, coverage = SuiteBootstrap(max_tests=self.max_tests).build(card, fingerprint)
        return SuitePreviewResult(
            agent_card=card,
            requirements_fingerprint=fingerprint,
            candidate_pool=pool,
            optimized_pack=pack,
            coverage=coverage,
            endpoint_probe=probe,
        )

    def init_from_prd_text(
        self,
        prd_text: str,
        *,
        agent_id: str,
        endpoint_url: str | None = None,
        probe_endpoint: bool = True,
        force_new_version: bool = False,
    ) -> SuiteInitResult:
        card, fingerprint, probe = AgentBootstrap.from_text(
            prd_text,
            agent_id=agent_id,
            endpoint_url=endpoint_url,
            probe_endpoint=probe_endpoint and endpoint_url is not None,
        )
        pool, pack, coverage = SuiteBootstrap(max_tests=self.max_tests).build(card, fingerprint)

        store = SuiteStore(self.suite_root)
        manifest = SuiteStore.new_manifest(card.id, fingerprint, endpoint_url or "")
        try:
            out = store.init_suite(manifest, pool, pack, force=force_new_version)
        except SuiteExistsError:
            raise

        derived = out / "derived_agent_card.json"
        derived.write_text(card.model_dump_json(indent=2), encoding="utf-8")
        if probe is not None:
            (out / "endpoint_probe.json").write_text(
                probe.model_dump_json(indent=2), encoding="utf-8"
            )

        return SuiteInitResult(
            suite_path=str(out),
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
    ) -> SuiteRunReport:
        store = SuiteStore(self.suite_root)
        manifest = store.load_manifest(agent_id)
        pack = store.load_pack(agent_id)

        url = endpoint_url or manifest.endpoint_profile
        if not url:
            raise ValueError("endpoint_url required when suite has no stored endpoint")

        previous_run = store.load_latest_run(agent_id)
        runner = BlackboxRunner(endpoint_url=url)
        report = runner.run_pack(pack)
        pool = store.load_pool(agent_id)
        coverage = CoverageMapper().report(pool, pack.tests)
        report.coverage_report = coverage

        if previous_run is not None:
            run_diff = diff_suite_runs(previous_run, report)
            if run_diff is not None:
                report.run_diff = run_diff.model_dump(mode="json")

        store.save_run(agent_id, report)
        return report

    def latest_run(self, agent_id: str) -> SuiteRunReport | None:
        return SuiteStore(self.suite_root).load_latest_run(agent_id)
