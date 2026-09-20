"""Agency-Agents Persona Introspector: parses markdown agent persona specifications."""

import re
from pathlib import Path
from typing import Any

import yaml

from agenteval.core.manifest import (
    AgentArchetype,
    AgentCapability,
    AgentCard,
    AgentInvariants,
)


class PersonaIntrospector:
    """Extracts structured AgentCard manifests from agency-agents markdown specifications."""

    @classmethod
    def parse_file(cls, path: Path | str) -> AgentCard:
        """Parse an agency-agent markdown persona file into an AgentCard."""
        file_path = Path(path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Persona file not found at: {file_path}")
        content = file_path.read_text(encoding="utf-8")
        return cls.parse_markdown(content, agent_id=file_path.stem)

    @classmethod
    def parse_markdown(cls, content: str, agent_id: str | None = None) -> AgentCard:
        """Parse raw markdown content with YAML frontmatter into an AgentCard."""
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            raise ValueError(
                "Invalid persona format: Must start with YAML frontmatter bounded by '---'."
            )

        fm_text = frontmatter_match.group(1)
        body_text = frontmatter_match.group(2)

        try:
            metadata: dict[str, Any] = yaml.safe_load(fm_text) or {}
        except Exception as e:
            raise ValueError(f"Failed to parse YAML frontmatter: {e}") from e

        name = str(metadata.get("name", "Unnamed Agent")).strip()
        description = str(metadata.get("description", "")).strip()
        vibe = str(metadata.get("vibe", "")).strip()

        # Derive clean unique ID
        if not agent_id:
            agent_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.lower()).strip("-")

        # Infer Archetype from metadata and name
        archetype = cls._infer_archetype(name, description, vibe)

        # Extract capabilities from Core Mission section
        capabilities = cls._extract_capabilities(body_text)

        # Extract invariants from Critical Rules section
        invariants = cls._extract_invariants(body_text)

        return AgentCard(
            id=agent_id,
            name=name,
            version="0.1.0",
            archetype=archetype,
            capabilities=capabilities,
            tools_required=[],
            tools_provided=[],
            invariants=invariants,
        )

    @classmethod
    def _infer_archetype(cls, name: str, description: str, vibe: str) -> AgentArchetype:
        """Classify agent into standard archetype based on persona text."""
        combined = f"{name} {description} {vibe}".lower()

        if any(
            k in combined
            for k in [
                "sre",
                "devops",
                "cloud",
                "infra",
                "incident",
                "database",
                "reliability",
                "tool",
            ]
        ):
            return AgentArchetype.TOOL_ACTION
        if any(
            k in combined
            for k in [
                "developer",
                "coding",
                "code",
                "frontend",
                "software",
                "typescript",
                "react",
                "vue",
            ]
        ):
            return AgentArchetype.CODING
        if any(
            k in combined for k in ["rag", "retrieval", "search", "knowledge graph", "documents"]
        ):
            return AgentArchetype.RAG
        if any(
            k in combined
            for k in ["sales", "deal", "support", "strategist", "community", "marketing", "coach"]
        ):
            return AgentArchetype.SUPPORT

        return AgentArchetype.TOOL_ACTION

    @classmethod
    def _extract_capabilities(cls, body: str) -> list[AgentCapability]:
        """Extract declared capabilities from markdown mission sections."""
        capabilities: list[AgentCapability] = []

        # Find Mission section specifically without crossing other ## headings
        mission_match = re.search(
            r"^##\s+[^#\n]*?Mission[^\n]*\n(.*?)(?=\n##\s+|\Z)",
            body,
            re.DOTALL | re.MULTILINE | re.IGNORECASE,
        )
        if not mission_match:
            return [AgentCapability(name="default_task", description="Execute core agent mission")]

        mission_content = mission_match.group(1).strip()

        # Look for ### headings
        if "###" in mission_content:
            subsections = re.split(r"\n###\s+", "\n" + mission_content)
            for sub in subsections:
                sub = sub.strip()
                if not sub:
                    continue
                lines = sub.splitlines()
                title = lines[0].strip()
                desc = " ".join(line.strip().lstrip("-* ") for line in lines[1:] if line.strip())
                capabilities.append(
                    AgentCapability(
                        name=title,
                        description=desc or title,
                    )
                )
        else:
            # Parse bullet items directly
            bullet_items = re.findall(r"^[*-]\s+(.+)$", mission_content, re.MULTILINE)
            for item in bullet_items[:10]:
                capabilities.append(
                    AgentCapability(
                        name=item[:40].strip(),
                        description=item.strip(),
                    )
                )

        if not capabilities:
            capabilities.append(
                AgentCapability(name="default_mission", description="Primary agent task")
            )

        return capabilities

    @classmethod
    def _extract_invariants(cls, body: str) -> AgentInvariants:
        """Extract operational invariants from Critical Rules markdown section."""
        rules_match = re.search(
            r"^##\s+[^#\n]*?Critical Rules[^\n]*\n(.*?)(?=\n##\s+|\Z)",
            body,
            re.DOTALL | re.MULTILINE | re.IGNORECASE,
        )
        if not rules_match:
            return AgentInvariants()

        rules_text = rules_match.group(1).lower()
        forbidden: list[str] = []

        if "never execute unverified destructive" in rules_text:
            forbidden.extend(["rm", "drop_table", "force_push"])

        return AgentInvariants(
            max_steps=10,
            forbidden_tools=forbidden,
            approval_required_tools=[],
        )
