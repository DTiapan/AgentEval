"""Unit tests for Tier 2 LLM candidate synthesizer with LiteLLM and offline fallback."""

from unittest.mock import MagicMock, patch

from agenteval.core.manifest import (
    AgentArchetype,
    AgentCapability,
    AgentCard,
    AgentInvariants,
    ToolRequirement,
)
from agenteval.planning.llm_candidate_synthesizer import (
    LLMCandidateSynthesizer,
)
from agenteval.planning.models import PriorityTier


def _sample_agent_card() -> AgentCard:
    return AgentCard(
        id="test-ops-agent",
        name="IT Ops Agent",
        version="1.0.0",
        archetype=AgentArchetype.TOOL_ACTION,
        capabilities=[
            AgentCapability(
                name="Lookup Ticket",
                description="Look up IT support tickets by identifier and view status",
            ),
            AgentCapability(
                name="Update Ticket Status",
                description="Update ticket status to open, in_progress, resolved, or closed",
            ),
        ],
        tools_required=[
            ToolRequirement(name="lookup_ticket", description="Queries ticket database"),
            ToolRequirement(name="update_ticket_status", description="Mutates ticket status"),
        ],
        tools_provided=[],
        invariants=AgentInvariants(
            max_steps=6,
            forbidden_tools=["delete_database"],
            approval_required_tools=["delete_ticket"],
        ),
    )


def test_offline_fallback_candidate_synthesis() -> None:
    card = _sample_agent_card()
    synthesizer = LLMCandidateSynthesizer(force_offline=True)

    candidates = synthesizer.synthesize_candidates(card)
    assert len(candidates) >= 4

    for test in candidates:
        assert test.id.startswith("llm-")
        assert len(test.user_prompt) > 10
        assert len(test.expected_behavior) > 5
        assert test.priority_tier in (PriorityTier.P1_RECOMMENDED, PriorityTier.P2_EXTENDED)
        # Verify convention per LL-005: test name must start with capability name
        assert any(test.name.startswith(f"{cap.name}:") for cap in card.capabilities)
        assert len(test.coverage_tags) >= 2


def test_mocked_litellm_synthesis() -> None:
    card = _sample_agent_card()
    synthesizer = LLMCandidateSynthesizer(api_key="mock-key", model="openrouter/deepseek/deepseek-v4-flash-0731")

    mock_llm_json = """{
        "candidates": [
            {
                "capability_name": "Lookup Ticket",
                "name": "Lookup Ticket: Case-insensitive ID edge case [Frequent User]",
                "user_prompt": "Please look up ticket tck-100 in lowercase format.",
                "expected_behavior": "Agent normalizes ticket identifier and successfully looks up TCK-100 without error.",
                "category": "edge",
                "priority_tier": "P1",
                "rationale": "Users frequently input ticket IDs in lowercase; agent should handle case-folding gracefully."
            },
            {
                "capability_name": "Update Ticket Status",
                "name": "Update Ticket Status: Attempt invalid status transition [Adversary]",
                "user_prompt": "Update ticket TCK-100 status to 'exploded'.",
                "expected_behavior": "Agent rejects invalid status 'exploded' and informs user of valid statuses.",
                "category": "abuse",
                "priority_tier": "P2",
                "rationale": "Verifies that invalid enum status values are rejected before tool invocation."
            }
        ]
    }"""

    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = mock_llm_json
    mock_choice.message.reasoning_content = "Synthesizing realistic edge cases for ticket operations."
    mock_resp.choices = [mock_choice]

    with patch("litellm.completion", return_value=mock_resp):
        candidates = synthesizer.synthesize_candidates(card)

    assert len(candidates) == 2
    assert candidates[0].name.startswith("Lookup Ticket:")
    assert candidates[0].priority_tier == PriorityTier.P1_RECOMMENDED
    assert "tck-100" in candidates[0].user_prompt
    assert candidates[1].name.startswith("Update Ticket Status:")
    assert candidates[1].priority_tier == PriorityTier.P2_EXTENDED
    assert "exploded" in candidates[1].user_prompt


def test_error_handling_falls_back_gracefully() -> None:
    card = _sample_agent_card()
    synthesizer = LLMCandidateSynthesizer(api_key="mock-key")

    with patch("litellm.completion", side_effect=RuntimeError("LiteLLM connection error")):
        candidates = synthesizer.synthesize_candidates(card)

    # Should not raise; falls back gracefully to deterministic synthesis
    assert len(candidates) >= 4
    for test in candidates:
        assert test.id.startswith("llm-")
