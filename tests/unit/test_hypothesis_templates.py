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
    assert "edge_context_overflow" in template_ids
    assert "edge_out_of_scope" in template_ids


def test_all_eight_mandatory_categories_are_covered() -> None:
    cap = AgentCapability(
        name="Enterprise Order Refund & Webhook Sync",
        description=(
            "Delete, refund, and mutate customer payment records, authenticate admin credentials, "
            "and sync external api webhook partner service"
        ),
    )
    generator = FailureHypothesisGenerator()
    hyps = generator.generate_for_capability(cap)
    mandatory_union = generator.infer_applicable_mandatory([cap])

    # All 8 MandatoryCategory values should be represented
    for expected_cat in MandatoryCategory:
        assert expected_cat in mandatory_union, f"Missing coverage for {expected_cat}"

    template_ids = {h.template_id for h in hyps}
    assert "security_data_isolation" in template_ids
    assert "security_privilege_escalation" in template_ids
    assert "security_tool_output_injection" in template_ids
    assert "security_critical_invariants" in template_ids
    assert "reliability_timeout_tolerance" in template_ids
    assert "reliability_schema_drift" in template_ids
    assert "reliability_graceful_degradation" in template_ids
    assert "functional_multi_step_dependency" in template_ids
    assert "functional_partial_failure" in template_ids
    assert "abuse_resource_exhaustion" in template_ids
    assert "abuse_state_tampering" in template_ids


def test_capability_signals_extracts_new_flags() -> None:
    from agenteval.planning.hypothesis_registry import capability_signals

    cap_multi = AgentCapability(
        name="Multi-Stage Process",
        description="Multi-step pipeline workflow lifecycle step",
    )
    sig_multi = capability_signals(cap_multi)
    assert sig_multi.has_multi_step

    cap_external = AgentCapability(
        name="Vendor Gateway",
        description="Call downstream third-party webhook partner",
    )
    sig_ext = capability_signals(cap_external)
    assert sig_ext.has_external_dependency

    cap_concurrency = AgentCapability(
        name="Reserve Seat",
        description="Shared inventory concurrent lock transaction",
    )
    sig_conc = capability_signals(cap_concurrency)
    assert sig_conc.has_concurrency

    cap_rate = AgentCapability(
        name="Batch Scraper",
        description="Bulk poll stream sync throttle",
    )
    sig_rate = capability_signals(cap_rate)
    assert sig_rate.has_rate_limit

    cap_ro = AgentCapability(
        name="Lookup Order Status",
        description="Read, view, search, and get order status",
    )
    sig_ro = capability_signals(cap_ro)
    assert sig_ro.is_read_only
    assert not sig_ro.is_mutating
