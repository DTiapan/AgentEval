"""Domain DTOs aligned with docs/design/domain-model.md (backbone, domain-agnostic)."""

from agenteval.domain.models import (
    AcceptanceCriterionRecord,
    FrozenTestCaseRecord,
    RequirementRecord,
)

__all__ = [
    "AcceptanceCriterionRecord",
    "FrozenTestCaseRecord",
    "RequirementRecord",
]
