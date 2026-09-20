"""Suite maintenance: prune tests for removed capabilities, extend for new ones (DR-011)."""

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentCard
from agenteval.planning._utils import slugify
from agenteval.planning.bootstrap import DEFAULT_PERSONAS, SuiteBootstrap
from agenteval.planning.coverage import CoverageMapper
from agenteval.planning.generator import CandidatePoolGenerator
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator
from agenteval.planning.models import (
    CandidateTest,
    OptimizerConfig,
    SuiteManifest,
    SuiteSyncChangelog,
    TestPack,
)
from agenteval.planning.optimizer import TestPackOptimizer
from agenteval.planning.suite_store import SuiteStore


class SuiteSyncResult(BaseModel):
    """Outcome of explicit suite sync (never runs on plain suite run)."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    previous_version: int
    new_version: int
    requirements_fingerprint: str
    removed_capabilities: list[str] = Field(default_factory=list)
    added_capabilities: list[str] = Field(default_factory=list)
    removed_test_ids: list[str] = Field(default_factory=list)
    pool_size: int
    pack_size: int
    noop: bool = False


class SuiteSyncOutcome(BaseModel):
    """In-memory sync result; persist when ``changelog`` is set."""

    model_config = ConfigDict(extra="forbid")

    result: SuiteSyncResult
    manifest: SuiteManifest | None = None
    pool: list[CandidateTest] | None = None
    pack: TestPack | None = None
    changelog: SuiteSyncChangelog | None = None


class SuiteSynchronizer:
    """Align frozen suite with an updated AgentCard manifest."""

    def __init__(self, max_tests: int = 10) -> None:
        self.max_tests = max_tests
        self._personas = DEFAULT_PERSONAS

    @staticmethod
    def capability_ids(card: AgentCard) -> set[str]:
        return {slugify(cap.name) for cap in card.capabilities}

    def compute_sync(
        self,
        *,
        agent_id: str,
        card: AgentCard,
        new_fingerprint: str,
        old_manifest: SuiteManifest,
        old_pool: list[CandidateTest],
        old_pack: TestPack,
        endpoint_profile: str | None = None,
    ) -> SuiteSyncOutcome:
        if card.id != agent_id:
            raise ValueError(
                f"Manifest agent id '{card.id}' does not match suite agent '{agent_id}'."
            )

        new_caps = self.capability_ids(card)
        if not new_caps:
            raise ValueError("Updated manifest has no capabilities; refusing to sync.")

        old_caps = {t.capability_id for t in old_pool}
        removed_caps = sorted(old_caps - new_caps)
        added_caps = sorted(new_caps - old_caps)

        if (
            not removed_caps
            and not added_caps
            and old_manifest.requirements_fingerprint == new_fingerprint
        ):
            return SuiteSyncOutcome(
                result=SuiteSyncResult(
                    agent_id=agent_id,
                    previous_version=old_manifest.version,
                    new_version=old_manifest.version,
                    requirements_fingerprint=new_fingerprint,
                    pool_size=len(old_pool),
                    pack_size=len(old_pack.tests),
                    noop=True,
                ),
            )

        pruned_pool = [t for t in old_pool if t.capability_id in new_caps]
        pruned_pack_tests = [t for t in old_pack.tests if t.capability_id in new_caps]
        archived = [t for t in old_pool if t.capability_id not in new_caps]
        removed_test_ids = [t.id for t in archived]

        pool = pruned_pool
        if added_caps:
            new_cap_objs = [c for c in card.capabilities if slugify(c.name) in added_caps]
            pool.extend(
                CandidatePoolGenerator().build_pool(card.id, new_cap_objs, self._personas)
            )

        hyp_gen = FailureHypothesisGenerator()
        config = OptimizerConfig(
            max_tests=self.max_tests,
            applicable_mandatory=hyp_gen.infer_applicable_mandatory(card.capabilities),
        )
        new_version = old_manifest.version + 1

        if added_caps:
            opt = TestPackOptimizer().optimize(
                card.id,
                pool,
                config,
                requirements_fingerprint=new_fingerprint,
                pack_version=new_version,
            )
            pack = opt.pack
            pack.candidate_count = len(pool)
        else:
            pack = TestPack(
                agent_id=card.id,
                version=new_version,
                tests=pruned_pack_tests,
                candidate_count=len(pool),
                requirements_fingerprint=new_fingerprint,
            )

        changelog = SuiteSyncChangelog(
            suite_version=new_version,
            timestamp=datetime.now(UTC).isoformat(),
            requirements_fingerprint=new_fingerprint,
            removed_capabilities=removed_caps,
            added_capabilities=added_caps,
            removed_test_ids=removed_test_ids,
            archived_tests=archived,
        )

        profile = endpoint_profile if endpoint_profile is not None else old_manifest.endpoint_profile
        updated_manifest = SuiteManifest(
            agent_id=old_manifest.agent_id,
            version=new_version,
            requirements_fingerprint=new_fingerprint,
            created_at=old_manifest.created_at,
            endpoint_profile=profile,
        )
        CoverageMapper().report_from_config(pool, pack.tests, config)

        return SuiteSyncOutcome(
            result=SuiteSyncResult(
                agent_id=agent_id,
                previous_version=old_manifest.version,
                new_version=new_version,
                requirements_fingerprint=new_fingerprint,
                removed_capabilities=removed_caps,
                added_capabilities=added_caps,
                removed_test_ids=removed_test_ids,
                pool_size=len(pool),
                pack_size=len(pack.tests),
            ),
            manifest=updated_manifest,
            pool=pool,
            pack=pack,
            changelog=changelog,
        )

    def sync(
        self,
        store: SuiteStore,
        agent_id: str,
        card: AgentCard,
        manifest_path: Path,
        prd_path: Path | None,
    ) -> SuiteSyncResult:
        new_fingerprint = SuiteBootstrap.fingerprint_files(manifest_path, prd_path)
        old_manifest = store.load_manifest(agent_id)
        old_pack = store.load_pack(agent_id)
        old_pool = store.load_pool(agent_id)
        outcome = self.compute_sync(
            agent_id=agent_id,
            card=card,
            new_fingerprint=new_fingerprint,
            old_manifest=old_manifest,
            old_pool=old_pool,
            old_pack=old_pack,
        )
        if outcome.changelog is not None and outcome.manifest and outcome.pool and outcome.pack:
            store.apply_sync(
                agent_id,
                outcome.manifest,
                outcome.pool,
                outcome.pack,
                outcome.changelog,
            )
        return outcome.result
