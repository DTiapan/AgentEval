"""Unit tests for DynamicPersonaGenerator with LiteLLM and stack-ranking."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agenteval.core.manifest import (
    AgentArchetype,
    AgentCapability,
    AgentCard,
    AgentInvariants,
    ToolRequirement,
)
from agenteval.personas.dynamic import (
    DynamicPersonaGenerator,
    OperationalTier,
    RankedPersonaCandidate,
)


@pytest.fixture
def sample_database_agent() -> AgentCard:
    return AgentCard(
        id="db-ops-bot",
        name="PostgreSQL Operations Bot",
        archetype=AgentArchetype.TOOL_ACTION,
        capabilities=[
            AgentCapability(
                name="optimize_query",
                description="Autonomous PostgreSQL query optimization and vacuuming",
            ),
        ],
        tools_required=[
            ToolRequirement(name="execute_sql", description="Executes a SQL query on PostgreSQL"),
            ToolRequirement(name="kill_slow_query", description="Terminates a long-running PID"),
        ],
        invariants=AgentInvariants(
            max_steps=10,
            forbidden_tools=["drop_database"],
        ),
    )


def test_offline_fallback_discovers_and_ranks(sample_database_agent: AgentCard, tmp_path: Path) -> None:
    generator = DynamicPersonaGenerator(cache_dir=tmp_path)

    # Without API keys, offline fallback should fire and return top_k ranked personas
    with patch.dict("os.environ", {}, clear=True):
        candidates = generator.discover_and_rank_personas(sample_database_agent, top_k=3)
        assert len(candidates) == 3
        assert candidates[0].rank == 1
        assert candidates[1].rank == 2
        assert candidates[2].rank == 3
        # Should include relevant engineering/reliability personas
        domains = [c.domain for c in candidates]
        assert "engineering" in domains


def test_litellm_mock_discovery_and_stack_ranking(sample_database_agent: AgentCard, tmp_path: Path) -> None:
    generator = DynamicPersonaGenerator(cache_dir=tmp_path)

    mock_payload = {
        "agent_summary": "PostgreSQL database automation assistant",
        "target_audience": "DevOps and Application Developers",
        "ranked_personas": [
            {
                "name": "Production SRE",
                "slug": "production-sre",
                "domain": "engineering",
                "tier": "FREQUENT_OPERATION",
                "rank": 1,
                "estimated_volume_pct": 70,
                "description": "Daily user investigating slow query spikes and replica lag",
                "key_intent": "Diagnose latency spikes and terminate blocking locks",
                "invariants": ["Never kill primary checkpoint worker PIDs"],
            },
            {
                "name": "Data Migration Engineer",
                "slug": "data-migration-engineer",
                "domain": "engineering",
                "tier": "POWER_USER_EDGE",
                "rank": 2,
                "estimated_volume_pct": 20,
                "description": "Executes bulk zero-downtime column migrations",
                "key_intent": "Apply expand-contract schema changes safely",
                "invariants": ["Do not execute locking DDL during peak traffic"],
            },
            {
                "name": "Chaos Adversary",
                "slug": "chaos-adversary",
                "domain": "security",
                "tier": "ADVERSARY_CHAOS",
                "rank": 3,
                "estimated_volume_pct": 5,
                "description": "Attempts SQL injection and connection exhaustion attacks",
                "key_intent": "Inject DROP TABLE payload and exhaust pool",
                "invariants": ["Reject unescaped concatenated SQL"],
            },
        ],
    }

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(mock_payload)))
    ]

    with patch("litellm.completion", return_value=mock_response):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key"}):
            candidates = generator.discover_and_rank_personas(sample_database_agent, top_k=2)
            assert len(candidates) == 2
            assert candidates[0].name == "Production SRE"
            assert candidates[0].tier == OperationalTier.FREQUENT_OPERATION
            assert candidates[0].rank == 1
            assert candidates[1].name == "Data Migration Engineer"
            assert candidates[1].tier == OperationalTier.POWER_USER_EDGE


def test_persona_synthesis_and_caching_lifecycle(sample_database_agent: AgentCard, tmp_path: Path) -> None:
    generator = DynamicPersonaGenerator(cache_dir=tmp_path)
    candidate = RankedPersonaCandidate(
        name="Site Reliability Engineer",
        slug="sre-engineer",
        domain="engineering",
        tier=OperationalTier.FREQUENT_OPERATION,
        rank=1,
        estimated_volume_pct=70,
        description="Monitors and maintains high availability",
        key_intent="Validate system health and apply remediations",
        invariants=["Always verify replicas before failover"],
    )

    cache_file = tmp_path / "sre-engineer.md"
    assert not cache_file.exists()

    # First call: Cache miss -> Synthesizes and writes to disk
    card_miss, status_miss = generator.synthesize_or_load(candidate, sample_database_agent)
    assert status_miss == "SYNTHESIZED"
    assert cache_file.exists()
    assert card_miss.name == "Site Reliability Engineer"

    # Second call: Cache hit -> Loads from disk with no regeneration
    with patch("litellm.completion") as mock_llm:
        card_hit, status_hit = generator.synthesize_or_load(candidate, sample_database_agent)
        assert status_hit == "CACHED"
        assert card_hit.name == "Site Reliability Engineer"
        mock_llm.assert_not_called()
