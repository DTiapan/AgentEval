"""Black-box test planning: models, pool optimization, and coverage reporting."""

from agenteval.planning.coverage import CoverageMapper
from agenteval.planning.generator import CandidatePoolGenerator, PersonaRef
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator
from agenteval.planning.models import (
    CandidateTest,
    CoverageReport,
    FailureHypothesis,
    MandatoryCategory,
    OptimizationResult,
    OptimizerConfig,
    ProvenanceLayer,
    TestPack,
)
from agenteval.planning.optimizer import TestPackOptimizer

__all__ = [
    "CandidatePoolGenerator",
    "CandidateTest",
    "CoverageMapper",
    "CoverageReport",
    "FailureHypothesis",
    "FailureHypothesisGenerator",
    "MandatoryCategory",
    "OptimizationResult",
    "OptimizerConfig",
    "PersonaRef",
    "ProvenanceLayer",
    "TestPack",
    "TestPackOptimizer",
]
