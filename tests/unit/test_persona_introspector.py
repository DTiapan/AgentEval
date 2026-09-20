"""Unit tests for PersonaIntrospector (agency-agents markdown parser)."""

from pathlib import Path

import pytest

from agenteval.core.manifest import AgentArchetype
from agenteval.introspect.persona import PersonaIntrospector


def test_parse_frontend_developer_persona() -> None:
    persona_path = Path("examples/agency_personas/engineering-frontend-developer.md")
    assert persona_path.exists(), "Benchmark persona file must exist"

    card = PersonaIntrospector.parse_file(persona_path)
    assert card.name == "Frontend Developer"
    assert card.id == "engineering-frontend-developer"
    assert card.archetype == AgentArchetype.CODING
    assert len(card.capabilities) >= 2
    assert any("Modern Web Applications" in cap.name for cap in card.capabilities)


def test_parse_sre_engineer_persona() -> None:
    persona_path = Path("examples/agency_personas/engineering-sre.md")
    card = PersonaIntrospector.parse_file(persona_path)

    assert card.name == "SRE Engineer"
    assert card.id == "engineering-sre"
    assert card.archetype == AgentArchetype.TOOL_ACTION
    assert len(card.capabilities) >= 1
    assert any("incident response" in cap.description.lower() for cap in card.capabilities)


def test_parse_deal_strategist_persona() -> None:
    persona_path = Path("examples/agency_personas/sales-deal-strategist.md")
    card = PersonaIntrospector.parse_file(persona_path)

    assert card.name == "Deal Strategist"
    assert card.id == "sales-deal-strategist"
    assert card.archetype == AgentArchetype.SUPPORT
    assert len(card.capabilities) >= 1


def test_parse_markdown_without_frontmatter_raises() -> None:
    raw_md = "# Raw Agent\n\nNo frontmatter here."
    with pytest.raises(ValueError, match="YAML frontmatter"):
        PersonaIntrospector.parse_markdown(raw_md)


def test_parse_file_not_found_raises() -> None:
    with pytest.raises(FileNotFoundError):
        PersonaIntrospector.parse_file("non_existent_persona.md")


def test_parse_markdown_with_fallback_defaults() -> None:
    raw_md = """---
name: Minimal Agent
---
# Minimal Agent
Just some content with no special sections.
"""
    card = PersonaIntrospector.parse_markdown(raw_md)
    assert card.name == "Minimal Agent"
    assert card.archetype == AgentArchetype.TOOL_ACTION
    assert len(card.capabilities) == 1
    assert card.capabilities[0].name == "default_task"
