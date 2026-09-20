"""On-the-fly Persona Synthesizer with local filesystem caching."""

from pathlib import Path

from agenteval.core.manifest import AgentCard
from agenteval.introspect.persona import PersonaIntrospector
from agenteval.personas.registry import PersonaCandidate


class PersonaSynthesizer:
    """Generates complete agent persona specifications on the fly and caches them locally."""

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        llm_api_key: str | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir or ".agenteval/personas")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.llm_api_key = llm_api_key

    def get_or_synthesize(
        self,
        candidate: PersonaCandidate,
        agent_context: str | None = None,
    ) -> tuple[AgentCard, bool]:
        """Fetch persona from local cache or synthesize on-the-fly.

        Returns:
            tuple of (AgentCard, is_cached: bool)
        """
        cached_file = self.cache_dir / f"{candidate.slug}.md"

        if cached_file.exists():
            card = PersonaIntrospector.parse_file(cached_file)
            return card, True

        # Cache Miss: Synthesize new persona markdown
        content = self._synthesize_markdown(candidate, agent_context=agent_context)
        cached_file.write_text(content, encoding="utf-8")

        card = PersonaIntrospector.parse_file(cached_file)
        return card, False

    def _synthesize_markdown(
        self,
        candidate: PersonaCandidate,
        agent_context: str | None = None,
    ) -> str:
        """Synthesize a complete agency-style markdown persona document."""
        # Clean formatting for rules and mission
        rules_text = (
            "\n".join(f"- {r}" for r in candidate.default_rules)
            or "- Execute only verified actions"
        )
        context_hint = f"\nSpecialized Context: {agent_context.strip()}" if agent_context else ""

        markdown = f"""---
name: {candidate.name}
description: {candidate.description}
color: blue
emoji: 🛡️
vibe: Professional, disciplined {candidate.domain} specialist adhering strictly to operational invariants.
---

# {candidate.name} Agent Personality

You are **{candidate.name}**, an expert specializing in {candidate.domain}.
{candidate.description}{context_hint}

## 🧠 Your Identity & Memory
- **Role**: {candidate.name}
- **Domain**: {candidate.domain}
- **Personality**: Detail-oriented, rigorous, safety-focused, technically precise
- **Experience**: Experienced in production-grade systems with high fault tolerance

## 🎯 Your Core Mission

### Core Operational Tasks
- Execute tasks within the {candidate.domain} domain with verified proof
- Monitor telemetry, validate inputs, and avoid silent failures
- Deliver measurable outcomes according to standard operating procedures

### Invariant Enforcement
- Ensure all actions are observable and verifiable
- Prevent duplicate mutations and respect rate constraints

## 🚨 Critical Rules You Must Follow
{rules_text}
- Maintain strict audit trail of environmental modifications
- Flag unverified assertions as UNVERIFIABLE
"""
        return markdown
