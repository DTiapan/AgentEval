"""Jev Persona Selector: matches agent DNA and intent to the top candidate personas."""

import json
import os
import urllib.error
import urllib.request
from typing import Any

from agenteval.core.manifest import AgentArchetype
from agenteval.personas.registry import PersonaCandidate, PersonaRegistry


class JevPersonaSelector:
    """TypeSafe AI / Jev powered selector identifying which personas best stress-test an agent."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        registry: PersonaRegistry | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY") or os.getenv("JEV_API_KEY")
        self.api_url: str = (
            api_url or os.getenv("TYPESAFE_API_URL") or "https://api.typesafe.ai/v1/persona-match"
        )
        self.registry = registry or PersonaRegistry()
        self.timeout_seconds = timeout_seconds

    def select_personas(
        self,
        context: str,
        tools: list[str] | None = None,
        archetype: AgentArchetype | None = None,
        limit: int = 3,
    ) -> list[PersonaCandidate]:
        """Select top candidate personas matching the agent's intent, tools, and archetype."""
        if not self.api_key:
            return self._local_select(context, tools=tools, archetype=archetype, limit=limit)

        payload: dict[str, Any] = {
            "context": context,
            "tools": tools or [],
            "archetype": archetype.value if archetype else None,
            "candidate_slugs": [p.slug for p in self.registry.list_all()],
            "limit": limit,
        }

        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(self.api_url, data=body_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                selected_slugs: list[str] = data.get("selected_slugs", [])
                results: list[PersonaCandidate] = []
                for s in selected_slugs[:limit]:
                    p = self.registry.get_by_slug(s)
                    if p:
                        results.append(p)
                if results:
                    return results
        except Exception:
            pass

        return self._local_select(context, tools=tools, archetype=archetype, limit=limit)

    def _local_select(
        self,
        context: str,
        tools: list[str] | None = None,
        archetype: AgentArchetype | None = None,
        limit: int = 3,
    ) -> list[PersonaCandidate]:
        """Deterministic keyword and archetype relevance matcher."""
        tools = tools or []
        combined_text = f"{context} {' '.join(tools)}".lower()

        scored: list[tuple[float, PersonaCandidate]] = []

        for candidate in self.registry.list_all():
            score = 0.0

            # 1. Archetype alignment
            if archetype and candidate.archetype == archetype:
                score += 2.0

            # 2. Keyword relevance
            for kw in candidate.keywords:
                if kw in combined_text:
                    score += 1.5

            # 3. Domain relevance
            if candidate.domain in combined_text:
                score += 1.0

            # 4. Name relevance
            if candidate.name.lower() in combined_text:
                score += 2.0

            if score > 0.0:
                scored.append((score, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            # Fallback to default diverse candidates
            return self.registry.list_all()[:limit]

        return [candidate for _, candidate in scored[:limit]]
