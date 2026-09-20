"""Declarative AgentCard manifest: defines agent capabilities, required tools, and invariants."""

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class AgentArchetype(StrEnum):
    """Standardized high-level functional agent archetypes."""

    TOOL_ACTION = "TOOL_ACTION"
    RAG = "RAG"
    CODING = "CODING"
    SUPPORT = "SUPPORT"
    SWARM = "SWARM"


class ToolRequirement(BaseModel):
    """External tool capability required by the agent in its environment."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Name of the required tool")
    description: str | None = Field(default=None, description="What the tool does")
    schema_def: dict[str, Any] | None = Field(
        default=None, alias="schema", description="Expected argument JSON schema"
    )
    required: bool = Field(default=True, description="Whether execution fails without this tool")


class AgentCapability(BaseModel):
    """Functional task or intent the agent is designed to fulfill."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Action or task identifier")
    description: str = Field(description="Explanation of task fulfillment")
    idempotency_supported: bool = Field(
        default=False, description="Whether agent supplies idempotency keys on retries"
    )


class AgentInvariants(BaseModel):
    """Strict operational boundaries and security constraints."""

    model_config = ConfigDict(extra="forbid")

    max_steps: int = Field(default=10, ge=1, description="Hard ceiling on loop iterations")
    forbidden_tools: list[str] = Field(
        default_factory=list, description="Tools the agent must never invoke"
    )
    approval_required_tools: list[str] = Field(
        default_factory=list, description="Destructive tools requiring human-in-the-loop approval"
    )


class AgentCard(BaseModel):
    """Declarative manifest specification for an agent under evaluation."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(description="Unique agent identifier")
    name: str = Field(description="Human-readable agent name")
    version: str = Field(default="0.1.0", description="Semantic version string")
    archetype: AgentArchetype = Field(
        default=AgentArchetype.TOOL_ACTION, description="Primary functional archetype"
    )
    capabilities: list[AgentCapability] = Field(
        default_factory=list, description="Declared capabilities"
    )
    tools_required: list[ToolRequirement] = Field(
        default_factory=list, description="Tools expected to be provided by environment"
    )
    tools_provided: list[ToolRequirement] = Field(
        default_factory=list, description="Tools exposed by the agent to other agents"
    )
    invariants: AgentInvariants = Field(default_factory=AgentInvariants)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentCard":
        """Instantiate an AgentCard from a dictionary."""
        return cls.model_validate(data)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "AgentCard":
        """Load and validate an AgentCard from a YAML file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"AgentCard manifest not found at: {file_path}")
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
