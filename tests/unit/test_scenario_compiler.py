"""Unit tests for ScenarioCompiler translating AgentCards & PRDs into executable scenarios."""

from pathlib import Path

from agenteval.core.manifest import AgentArchetype, AgentCapability, AgentCard, ToolRequirement
from agenteval.scenarios.compiler import ScenarioCompiler
from agenteval.scenarios.schema import TestScenario


def test_compile_from_agent_card() -> None:
    card = AgentCard(
        id="devops-agent",
        name="DevOps Agent",
        archetype=AgentArchetype.TOOL_ACTION,
        capabilities=[
            AgentCapability(
                name="deploy_service", description="Deploy container to Kubernetes cluster"
            ),
        ],
        tools_required=[
            ToolRequirement(name="kubectl_apply", description="Apply k8s manifest"),
        ],
    )

    scenarios = ScenarioCompiler.compile_scenarios(card, include_chaos=True)
    assert len(scenarios) == 2

    # Baseline scenario
    baseline = scenarios[0]
    assert isinstance(baseline, TestScenario)
    assert baseline.id == "devops-agent-deploy-service-baseline"
    assert "kubectl_apply" in baseline.expected_tools
    assert len(baseline.fault_rules) == 0

    # Chaos scenario
    chaos = scenarios[1]
    assert isinstance(chaos, TestScenario)
    assert chaos.id == "devops-agent-deploy-service-chaos"
    assert len(chaos.fault_rules) == 1
    assert chaos.fault_rules[0].tool_name == "kubectl_apply"


def test_compile_from_persona_file() -> None:
    persona_path = Path("examples/agency_personas/engineering-sre.md")
    scenarios = ScenarioCompiler.compile_from_persona(persona_path)

    assert len(scenarios) >= 1
    for sc in scenarios:
        assert isinstance(sc, TestScenario)
        assert "SRE Engineer" in sc.name
        assert len(sc.user_prompt) > 0


def test_compile_from_prd_text() -> None:
    prd_text = """
    # Requirements Document
    1. Feature: Query user orders and return shipping status.
    2. Feature: Cancel pending order if unfulfilled.
    """
    scenarios = ScenarioCompiler.compile_from_prd(prd_text, agent_name="Order Assistant")
    assert len(scenarios) == 2
    assert any("shipping status" in sc.user_prompt.lower() for sc in scenarios)
    assert any("cancel" in sc.user_prompt.lower() for sc in scenarios)
