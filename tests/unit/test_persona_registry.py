"""Unit tests for the 50+ candidate Persona Taxonomy & Registry."""

from agenteval.core.manifest import AgentArchetype
from agenteval.personas.registry import PersonaRegistry


def test_registry_contains_curated_personas() -> None:
    registry = PersonaRegistry()
    personas = registry.list_all()

    assert len(personas) >= 30, "Registry should contain a rich catalog of candidate personas"
    assert any(p.slug == "sre-engineer" for p in personas)
    assert any(p.slug == "frontend-developer" for p in personas)
    assert any(p.slug == "database-reliability-engineer" for p in personas)
    assert any(p.slug == "sales-deal-strategist" for p in personas)


def test_registry_lookup_by_slug() -> None:
    registry = PersonaRegistry()
    persona = registry.get_by_slug("sre-engineer")

    assert persona is not None
    assert persona.name == "SRE Engineer"
    assert persona.domain == "engineering"
    assert persona.archetype == AgentArchetype.TOOL_ACTION
    assert len(persona.keywords) > 0


def test_registry_filter_by_domain() -> None:
    registry = PersonaRegistry()
    eng_personas = registry.filter_by_domain("engineering")
    sales_personas = registry.filter_by_domain("sales")

    assert len(eng_personas) > 0
    assert len(sales_personas) > 0
    assert all(p.domain == "engineering" for p in eng_personas)
    assert all(p.domain == "sales" for p in sales_personas)


def test_registry_search() -> None:
    registry = PersonaRegistry()
    results = registry.search("kubernetes docker deploy")
    assert len(results) > 0
    assert results[0].slug == "devops-automator"
