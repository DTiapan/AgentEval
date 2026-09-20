"""Unit tests for PersonaSynthesizer and local file caching."""

from pathlib import Path

from agenteval.core.manifest import AgentArchetype, AgentCard
from agenteval.personas.registry import PersonaCandidate
from agenteval.personas.synthesizer import PersonaSynthesizer


def test_synthesizer_cache_miss_creates_file(tmp_path: Path) -> None:
    cache_dir = tmp_path / "personas"
    synthesizer = PersonaSynthesizer(cache_dir=cache_dir)

    candidate = PersonaCandidate(
        slug="security-auditor",
        name="Security Auditor",
        domain="security",
        archetype=AgentArchetype.TOOL_ACTION,
        description="OWASP Top 10 vulnerability scanner and prompt injection auditor.",
        keywords=["security", "audit", "injection"],
        default_rules=["Zero trust verification", "Never leak sensitive credentials"],
    )

    card, is_cached = synthesizer.get_or_synthesize(candidate)

    assert is_cached is False
    assert isinstance(card, AgentCard)
    assert card.name == "Security Auditor"
    assert card.archetype == AgentArchetype.TOOL_ACTION

    # Verify file was written to disk
    cached_file = cache_dir / "security-auditor.md"
    assert cached_file.exists()
    content = cached_file.read_text(encoding="utf-8")
    assert "name: Security Auditor" in content
    assert "## 🎯 Your Core Mission" in content
    assert "## 🚨 Critical Rules You Must Follow" in content


def test_synthesizer_cache_hit_reuses_file(tmp_path: Path) -> None:
    cache_dir = tmp_path / "personas"
    synthesizer = PersonaSynthesizer(cache_dir=cache_dir)

    candidate = PersonaCandidate(
        slug="security-auditor",
        name="Security Auditor",
        domain="security",
        archetype=AgentArchetype.TOOL_ACTION,
        description="OWASP Top 10 vulnerability scanner.",
    )

    # 1st call: creates file
    card1, is_cached1 = synthesizer.get_or_synthesize(candidate)
    assert is_cached1 is False

    # 2nd call: must hit cache
    card2, is_cached2 = synthesizer.get_or_synthesize(candidate)
    assert is_cached2 is True
    assert card1.name == card2.name
    assert card1.id == card2.id
