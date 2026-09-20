"""North Star entry: functional requirements → AgentCard (E1)."""

import hashlib
import re
from pathlib import Path

from agenteval.core.manifest import AgentCapability, AgentCard, AgentInvariants
from agenteval.introspect.persona import PersonaIntrospector


class RequirementsIngestor:
    """Parse PRD / requirements markdown into a declarative AgentCard."""

    @classmethod
    def fingerprint(cls, prd_path: Path) -> str:
        return cls.fingerprint_text(prd_path.read_text(encoding="utf-8"))

    @classmethod
    def fingerprint_text(cls, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return digest[:16]

    @classmethod
    def from_file(cls, prd_path: Path, agent_id: str | None = None) -> AgentCard:
        text = prd_path.read_text(encoding="utf-8")
        stem = agent_id or prd_path.stem
        return cls.from_text(text, agent_id=stem, display_name=cls._title_from_text(text, stem))

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        agent_id: str,
        display_name: str | None = None,
    ) -> AgentCard:
        name = display_name or agent_id.replace("-", " ").title()
        capabilities = cls._parse_capabilities(text)
        archetype = PersonaIntrospector._infer_archetype(name, text[:500], "")
        return AgentCard(
            id=agent_id,
            name=name,
            version="0.1.0",
            archetype=archetype,
            capabilities=capabilities,
            tools_required=[],
            invariants=AgentInvariants(max_steps=10),
        )

    @staticmethod
    def _title_from_text(text: str, fallback: str) -> str:
        match = re.search(r"^#\s+(.+)$", text.strip(), re.MULTILINE)
        if match:
            title = match.group(1).strip()
            return re.sub(r"\s*—\s*Requirements\s*$", "", title, flags=re.IGNORECASE).strip()
        return fallback.replace("-", " ").title()

    @classmethod
    def _parse_capabilities(cls, text: str) -> list[AgentCapability]:
        capabilities: list[AgentCapability] = []

        section_blocks = re.findall(
            r"^##\s+([^\n]+)\n(.*?)(?=\n##\s+|\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        for heading, body in section_blocks:
            heading_lower = heading.strip().lower()
            is_cap_section = "requirement" in heading_lower or "capabilit" in heading_lower
            is_invariant_section = "invariant" in heading_lower or "security" in heading_lower
            if not is_cap_section and not is_invariant_section:
                continue
            bullets = cls._bullets_from_body(body)
            if bullets:
                for bullet in bullets:
                    capabilities.append(
                        AgentCapability(
                            name=cls._short_name(bullet),
                            description=bullet,
                        )
                    )
                continue
            desc = " ".join(line.strip() for line in body.strip().splitlines() if line.strip())
            if not desc:
                continue
            cap_name = cls._capability_name_from_heading(heading, desc)
            capabilities.append(AgentCapability(name=cap_name, description=desc))

        if capabilities:
            return capabilities

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lower = stripped.lower()
            if not any(m in lower for m in ("must", "should", "shall", "requirement", "feature:")):
                continue
            if re.match(r"^\d+\.\s+", stripped):
                stripped = re.sub(r"^\d+\.\s+", "", stripped)
            clean = (
                stripped.replace("Feature:", "")
                .replace("Requirement:", "")
                .strip()
            )
            if len(clean) < 8:
                continue
            capabilities.append(
                AgentCapability(
                    name=cls._short_name(clean),
                    description=clean,
                )
            )

        if capabilities:
            return capabilities[:12]

        mission_caps = PersonaIntrospector._extract_capabilities(text)
        if mission_caps and mission_caps[0].name not in ("default_task", "default_mission"):
            return mission_caps

        if not capabilities:
            capabilities.append(
                AgentCapability(
                    name="Core agent behavior",
                    description="Fulfill the functional requirements document.",
                )
            )
        return capabilities[:12]

    @staticmethod
    def _bullets_from_body(body: str) -> list[str]:
        items: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            match = re.match(r"^[-*]\s+(.+)$", stripped)
            if match:
                text = match.group(1).strip()
                if len(text) >= 8:
                    items.append(text)
        return items

    @staticmethod
    def _capability_name_from_heading(heading: str, description: str) -> str:
        num = re.search(r"(\d+)", heading)
        if num:
            return f"Requirement {num.group(1)}"
        return RequirementsIngestor._short_name(description)

    @staticmethod
    def _short_name(description: str, max_len: int = 48) -> str:
        words = re.sub(r"[^a-zA-Z0-9\s]", "", description).split()
        snippet = " ".join(words[:6])
        if len(snippet) > max_len:
            snippet = snippet[: max_len - 3].rsplit(" ", 1)[0]
        return snippet or "Requirement"
