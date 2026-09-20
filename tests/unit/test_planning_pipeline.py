"""Integration: pool generation + optimization (B1 + B2 + B4)."""

from agenteval.core.manifest import AgentCapability
from agenteval.planning.generator import CandidatePoolGenerator, PersonaRef
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator
from agenteval.planning.models import OptimizerConfig
from agenteval.planning.optimizer import TestPackOptimizer


def test_refund_pool_optimizes_smaller_than_raw_count() -> None:
    caps = [
        AgentCapability(
            name="Issue Refund",
            description="Process customer refund for a valid order payment",
        ),
    ]
    personas = [
        PersonaRef(slug="frequent-user", name="Frequent User", framing="customer"),
        PersonaRef(slug="adversary", name="Adversary", framing="attacker"),
        PersonaRef(slug="auditor", name="Auditor", framing="security reviewer"),
    ]
    pool = CandidatePoolGenerator().build_pool("refund-bot", caps, personas)
    hyp_gen = FailureHypothesisGenerator()
    config = OptimizerConfig(
        max_tests=10,
        applicable_mandatory=hyp_gen.infer_applicable_mandatory(caps),
    )
    result = TestPackOptimizer().optimize("refund-bot", pool, config)
    assert result.pack.candidate_count == len(pool)
    assert len(result.pack.tests) <= 10
    assert len(result.pack.tests) < len(pool)
    assert not result.mandatory_missing
