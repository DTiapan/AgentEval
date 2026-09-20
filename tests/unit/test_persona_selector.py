"""Unit tests for JevPersonaSelector matching agent context to candidate personas."""

from unittest.mock import MagicMock, patch

import pytest

from agenteval.core.manifest import AgentArchetype
from agenteval.personas.registry import PersonaCandidate
from agenteval.recommender.persona_selector import JevPersonaSelector


def test_select_personas_for_database_agent() -> None:
    selector = JevPersonaSelector()
    matches = selector.select_personas(
        context="PostgreSQL database query executor and schema migration assistant",
        tools=["execute_sql", "migrate_schema", "rollback_transaction"],
        archetype=AgentArchetype.TOOL_ACTION,
        limit=2,
    )

    assert len(matches) == 2
    slugs = [p.slug for p in matches]
    assert "database-reliability-engineer" in slugs or "sre-engineer" in slugs
    assert all(isinstance(p, PersonaCandidate) for p in matches)


def test_select_personas_for_frontend_agent() -> None:
    selector = JevPersonaSelector()
    matches = selector.select_personas(
        context="Build responsive React components with TypeScript and Tailwind CSS",
        tools=["render_component", "check_accessibility"],
        archetype=AgentArchetype.CODING,
        limit=2,
    )

    assert len(matches) >= 1
    assert matches[0].slug == "frontend-developer"


def test_select_personas_for_sales_agent() -> None:
    selector = JevPersonaSelector()
    matches = selector.select_personas(
        context="Inbound sales lead qualifier evaluating budget and decision criteria",
        tools=["score_lead", "draft_proposal"],
        archetype=AgentArchetype.SUPPORT,
        limit=2,
    )

    assert len(matches) >= 1
    slugs = [p.slug for p in matches]
    assert "sales-deal-strategist" in slugs or "outbound-strategist" in slugs


def test_select_personas_remote_jev_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JEV_API_KEY", "mock_key")
    selector = JevPersonaSelector()

    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"selected_slugs": ["sre-engineer", "backend-architect"]}'
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        matches = selector.select_personas("Incident mitigation system", limit=2)
        assert len(matches) == 2
        assert matches[0].slug == "sre-engineer"
        assert matches[1].slug == "backend-architect"
