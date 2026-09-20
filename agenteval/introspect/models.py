"""Domain models for agent DNA and introspected tool signatures."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentArchetype


class IntrospectedTool(BaseModel):
    """Tool signature discovered via introspection protocols (MCP, OpenAPI, Python)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Unique tool identifier")
    description: str | None = Field(default=None, description="Tool description or docstring")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="JSON schema or argument type definitions"
    )
    required_args: list[str] = Field(
        default_factory=list, description="Names of mandatory arguments"
    )


class AgentDNA(BaseModel):
    """Normalized structural and intent signals extracted from an agent."""

    model_config = ConfigDict(extra="forbid")

    tools: list[IntrospectedTool] = Field(default_factory=list)
    prompt_intent: str | None = Field(default=None)
    declared_archetype: AgentArchetype | None = Field(default=None)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
