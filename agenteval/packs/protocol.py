"""Pack and connector types (ADR-006 / pack-interface.md)."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class PackManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    display_name: str
    description: str = ""
    slots_filled: list[str] = Field(default_factory=list)


class RequirementDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stable_id: str
    statement: str
    pack_name: str


class ComplianceControlDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_key: str
    title: str
    pack_name: str
    requirement_stable_ids: list[str] = Field(default_factory=list)


@runtime_checkable
class DomainPack(Protocol):
    """Installed domain pack (entry point: agenteval.domain_packs)."""

    @property
    def manifest(self) -> PackManifest: ...

    def contribute_options(self) -> dict[str, object]: ...

    def mandatory_requirements(self, options: dict[str, object]) -> list[RequirementDraft]: ...

    def compliance_controls(self) -> list[ComplianceControlDraft]: ...
