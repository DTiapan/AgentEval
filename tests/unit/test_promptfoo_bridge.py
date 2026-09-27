"""Unit tests for PromptFoo adversarial red-team bridge and config export."""

import json

from agenteval.core.manifest import (
    AgentArchetype,
    AgentCapability,
    AgentCard,
    AgentInvariants,
    ToolRequirement,
)
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.models import MandatoryCategory, PriorityTier
from agenteval.planning.promptfoo_bridge import (
    PromptFooAttackPlugin,
    PromptFooBridge,
)


def _sample_agent_card() -> AgentCard:
    return AgentCard(
        id="test-billing-agent",
        name="Billing Agent",
        version="1.0.0",
        archetype=AgentArchetype.TOOL_ACTION,
        capabilities=[
            AgentCapability(
                name="Process Customer Refund",
                description="Process eligible refunds for customer transactions and store audit records",
            )
        ],
        tools_required=[
            ToolRequirement(name="issue_refund", description="Issues refund to payment gateway"),
            ToolRequirement(name="query_transactions", description="Queries transaction history"),
        ],
        tools_provided=[],
        invariants=AgentInvariants(
            max_steps=8,
            forbidden_tools=["delete_customer_account"],
            approval_required_tools=["issue_refund"],
        ),
    )


def test_promptfoo_bridge_cli_available_flag() -> None:
    bridge = PromptFooBridge(executable_path="/nonexistent/bin/promptfoo")
    # Should safely check without crashing
    assert isinstance(bridge.is_cli_available(), bool)


def test_generate_adversarial_candidates_coverage() -> None:
    card = _sample_agent_card()
    bridge = PromptFooBridge()

    candidates = bridge.generate_adversarial_candidates(card)
    assert len(candidates) >= 5

    # Check for prompt injection
    pi_tests = [c for c in candidates if "prompt-injection" in c.id]
    assert len(pi_tests) >= 1
    assert pi_tests[0].priority_tier == PriorityTier.P0_CRITICAL
    assert MandatoryCategory.PROMPT_INJECTION in pi_tests[0].mandatory_categories

    # Check for BOLA / parameter tampering targeting issue_refund
    bola_tests = [c for c in candidates if "bola" in c.id]
    assert len(bola_tests) >= 1
    assert bola_tests[0].priority_tier == PriorityTier.P0_CRITICAL
    assert MandatoryCategory.AUTHORIZATION in bola_tests[0].mandatory_categories
    assert "issue_refund" in bola_tests[0].user_prompt

    # Check for PII leakage
    pii_tests = [c for c in candidates if "pii" in c.id]
    assert len(pii_tests) >= 1
    assert pii_tests[0].priority_tier == PriorityTier.P0_CRITICAL
    assert MandatoryCategory.SENSITIVE_DATA_LEAKAGE in pii_tests[0].mandatory_categories

    # Check for DoS / recursive explosion (P2 Extended)
    dos_tests = [c for c in candidates if "dos" in c.id]
    assert len(dos_tests) >= 1
    assert dos_tests[0].priority_tier == PriorityTier.P2_EXTENDED

    # Check for SQL injection (P2 Extended)
    sqli_tests = [c for c in candidates if "sql" in c.id]
    assert len(sqli_tests) >= 1
    assert sqli_tests[0].priority_tier == PriorityTier.P2_EXTENDED


def test_generate_adversarial_candidates_custom_plugins() -> None:
    card = _sample_agent_card()
    bridge = PromptFooBridge()

    candidates = bridge.generate_adversarial_candidates(
        card,
        plugins=[PromptFooAttackPlugin.PROMPT_INJECTION, PromptFooAttackPlugin.ROLE_HIJACK],
    )
    assert len(candidates) == 2
    categories = {c.failure_mode for c in candidates}
    assert "prompt_injection_delimiter" in categories
    assert "role_hijack_escalation" in categories


def test_generate_adversarial_candidates_empty_capabilities() -> None:
    card = AgentCard(
        id="empty-agent",
        name="Empty Agent",
        version="1.0.0",
        archetype=AgentArchetype.TOOL_ACTION,
        capabilities=[],
        tools_required=[],
        tools_provided=[],
        invariants=AgentInvariants(max_steps=5, forbidden_tools=[], approval_required_tools=[]),
    )
    bridge = PromptFooBridge()
    candidates = bridge.generate_adversarial_candidates(card)
    assert candidates == []


def test_export_promptfoo_config_and_json() -> None:
    card = _sample_agent_card()
    bridge = PromptFooBridge()
    candidates = bridge.generate_adversarial_candidates(card)

    endpoint = "http://127.0.0.1:8770/chat"
    config = bridge.export_promptfoo_config(candidates, endpoint)

    assert config.description.startswith("AgentEval Adversarial")
    assert len(config.tests) == len(candidates)
    assert config.providers[0]["id"] == f"webhook:{endpoint}"

    json_str = bridge.export_promptfoo_json(candidates, endpoint)
    parsed = json.loads(json_str)
    assert parsed["prompts"] == ["{{prompt}}"]
    assert len(parsed["tests"]) == len(candidates)
    assert "assert" in parsed["tests"][0]


def test_suite_bootstrap_includes_adversarial_candidates() -> None:
    card = _sample_agent_card()
    bootstrap = SuiteBootstrap(max_tests=15)
    pool, pack, coverage = bootstrap.build(card, "fp-1234")

    # The pool should contain both standard hypothesis candidates and adversarial red-team probes
    redteam_in_pool = [t for t in pool if t.id.startswith("redteam-")]
    assert len(redteam_in_pool) >= 4

    # Pack should have coverage report with all mandatory categories evaluated
    assert len(coverage.covered_tags) > 0
    assert len(coverage.axes) > 0
