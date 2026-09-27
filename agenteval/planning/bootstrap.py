"""Bootstrap candidate pool + optimized pack from AgentCard (suite init)."""

import hashlib
from pathlib import Path

from agenteval.core.manifest import AgentCard
from agenteval.planning.coverage import CoverageMapper
from agenteval.planning.generator import CandidatePoolGenerator, PersonaRef
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator
from agenteval.planning.jev_candidate_scorer import JevCandidateScorer
from agenteval.planning.models import (
    CandidateTest,
    CoverageReport,
    OptimizerConfig,
    PriorityTier,
    TestPack,
)
from agenteval.planning.optimizer import TestPackOptimizer

DEFAULT_PERSONAS: list[PersonaRef] = [
    PersonaRef(slug="frequent-user", name="Frequent User", framing="a regular customer"),
    PersonaRef(slug="adversary", name="Adversary", framing="a potentially malicious user"),
    PersonaRef(
        slug="security-auditor",
        name="Security Auditor",
        framing="a compliance reviewer testing boundaries",
    ),
]


class SuiteBootstrap:
    """Generate pool and optimized pack without LLM (personas are defaults unless extended)."""

    def __init__(
        self,
        max_tests: int = 12,
        personas: list[PersonaRef] | None = None,
        scorer: JevCandidateScorer | None = None,
    ) -> None:
        self.max_tests = max_tests
        self.personas = personas or DEFAULT_PERSONAS
        self.scorer = scorer or JevCandidateScorer()

    @staticmethod
    def fingerprint_manifest(card: AgentCard, extra_text: str = "") -> str:
        payload = card.model_dump_json() + extra_text
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def fingerprint_files(manifest_path: Path, prd_path: Path | None = None) -> str:
        parts = [manifest_path.read_bytes()]
        if prd_path and prd_path.exists():
            parts.append(prd_path.read_bytes())
        digest = hashlib.sha256(b"".join(parts)).hexdigest()
        return digest[:16]

    @staticmethod
    def fingerprint_prd(prd_path: Path) -> str:
        digest = hashlib.sha256(prd_path.read_bytes()).hexdigest()
        return digest[:16]

    def build(
        self,
        card: AgentCard,
        requirements_fingerprint: str,
        *,
        max_tier: PriorityTier | None = None,
        selected_test_ids: list[str] | None = None,
    ) -> tuple[list[CandidateTest], TestPack, CoverageReport]:
        capabilities = card.capabilities
        if not capabilities:
            raise ValueError("AgentCard has no capabilities; cannot generate suite.")

        pool = CandidatePoolGenerator().build_pool(card.id, capabilities, self.personas)
        from agenteval.planning.promptfoo_bridge import PromptFooBridge

        adversarial_tests = PromptFooBridge().generate_adversarial_candidates(card)
        existing_ids = {t.id for t in pool}
        for adv in adversarial_tests:
            if adv.id not in existing_ids:
                pool.append(adv)
                existing_ids.add(adv.id)

        from agenteval.planning.llm_candidate_synthesizer import LLMCandidateSynthesizer

        synthesized_tests = LLMCandidateSynthesizer(personas=self.personas).synthesize_candidates(card)
        for syn in synthesized_tests:
            if syn.id not in existing_ids:
                pool.append(syn)
                existing_ids.add(syn.id)

        # Tier 3: Quality filter and rank the candidate pool (prune duplicates and slop)
        pool, _score_map = self.scorer.filter_and_rank_pool(pool)

        hyp_gen = FailureHypothesisGenerator()
        applicable = set(hyp_gen.infer_applicable_mandatory(capabilities))
        for adv in adversarial_tests:
            applicable.update(adv.mandatory_categories)

        config = OptimizerConfig(
            max_tests=self.max_tests,
            applicable_mandatory=sorted(applicable, key=lambda m: m.value),
            max_tier=max_tier,
            selected_test_ids=selected_test_ids,
        )
        opt = TestPackOptimizer().optimize(
            card.id,
            pool,
            config,
            requirements_fingerprint=requirements_fingerprint,
        )
        coverage = CoverageMapper().report_from_config(pool, opt.pack.tests, config)
        return pool, opt.pack, coverage
