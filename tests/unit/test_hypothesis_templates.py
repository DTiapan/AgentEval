"""Tests for rule-based failure hypothesis templates (B1)."""

from agenteval.core.manifest import AgentCapability
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator
from agenteval.planning.models import MandatoryCategory


def test_always_includes_functional_and_edge_hypotheses() -> None:
    cap = AgentCapability(name="Greet User", description="Say hello to the visitor")
    hyps = FailureHypothesisGenerator().generate_for_capability(cap)
    template_ids = {h.template_id for h in hyps}
    assert "functional_happy_path" in template_ids
    assert "functional_invalid_input" in template_ids
    assert "edge_empty_input" in template_ids
    assert "edge_ambiguous_request" in template_ids


def test_refund_capability_gets_security_and_abuse_templates() -> None:
    cap = AgentCapability(
        name="Issue Refund",
        description="Process customer refund for a valid order payment",
    )
    hyps = FailureHypothesisGenerator().generate_for_capability(cap)
    template_ids = {h.template_id for h in hyps}
    assert "security_authorization" in template_ids
    assert "security_prompt_injection" in template_ids
    assert "abuse_duplicate_action" in template_ids
    auth = next(h for h in hyps if h.template_id == "security_authorization")
    assert MandatoryCategory.AUTHORIZATION in auth.mandatory_categories
    assert any(t.startswith("cap:") for t in auth.coverage_tags)


def test_read_only_capability_skips_mutator_security_floor() -> None:
    cap = AgentCapability(
        name="Search Docs",
        description="Read-only search across public documentation",
    )
    hyps = FailureHypothesisGenerator().generate_for_capability(cap)
    template_ids = {h.template_id for h in hyps}
    assert "security_prompt_injection" not in template_ids
    assert "abuse_duplicate_action" not in template_ids
