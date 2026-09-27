"""Tests for candidate test pool generator (B2)."""

from agenteval.core.manifest import AgentCapability
from agenteval.planning.generator import CandidatePoolGenerator, PersonaRef
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator


def test_pool_is_persona_times_hypotheses_bounded() -> None:
    caps = [
        AgentCapability(name="Issue Refund", description="Refund a paid order for the customer"),
    ]
    personas = [
        PersonaRef(slug="frequent-user", name="Frequent User", framing="a regular customer"),
        PersonaRef(slug="adversary", name="Adversary", framing="a malicious actor"),
    ]
    hyps = FailureHypothesisGenerator().generate_for_capability(caps[0])
    gen = CandidatePoolGenerator()
    pool = gen.build_pool("agent-refund", caps, personas)
    assert len(pool) == len(hyps) * len(personas)
    expected_cap_id = caps[0].requirement_id()
    assert all(t.capability_id == expected_cap_id for t in pool)
    assert all(t.persona_id in {"frequent-user", "adversary"} for t in pool)
    assert all(t.template_id is not None for t in pool)


def test_pool_ids_are_stable_and_unique() -> None:
    caps = [AgentCapability(name="Order Status", description="Check order status")]
    personas = [PersonaRef(slug="user", name="User", framing="a shopper")]
    pool = CandidatePoolGenerator().build_pool("shop", caps, personas)
    ids = [t.id for t in pool]
    assert len(ids) == len(set(ids))
