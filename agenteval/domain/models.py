"""Pydantic records for normalized suite freeze (SQLite v2)."""

from pydantic import BaseModel, ConfigDict, Field


class RequirementRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    suite_version_id: str
    stable_id: str
    statement: str
    source_kind: str = Field(pattern="^(spec|pack)$")
    review_status: str = Field(default="approved")


class AcceptanceCriterionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    requirement_id: str
    stable_id: str
    description: str
    evidence_kind: str
    check_kind: str
    source_kind: str = Field(default="extracted")


class FrozenTestCaseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    suite_version_id: str
    stable_id: str
    title: str
    persona_json: str
    inputs_json: str
    test_data_json: str
    criterion_ids: list[str] = Field(default_factory=list)
