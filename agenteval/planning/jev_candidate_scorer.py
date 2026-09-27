"""Tier 3 Jev multi-axis candidate quality filter and scorer.

Evaluates synthesized candidate tests across 4 dimensions before set-cover optimization:
1. Severity: Impact of failure (critical floor vs minor formatting).
2. Novelty: Linguistic & semantic uniqueness against the current candidate pool.
3. Flakiness Risk: Ambiguity, non-deterministic phrasing, or missing assertions.
4. Execution Cost: Relative token length and tool execution overhead.

Prunes redundant or low-value candidate tests while preserving mandatory security floors.
"""

from __future__ import annotations

import re
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from agenteval.planning.models import (
    CandidateTest,
    PriorityTier,
)

# Vague or unassertive phrasing that indicates high test flakiness or slop
_VAGUE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\b(maybe|stuff|whatever|something|somehow|do\s+things)\b", re.IGNORECASE),
    re.compile(r"\b(try\s+to|see\s+if|perhaps|anything)\b", re.IGNORECASE),
    re.compile(r"\b(something\s+happens|it\s+works)\b", re.IGNORECASE),
)

# Concrete identifier patterns (e.g. TCK-100, REF-1234, ID: 55, UUID)
_CONCRETE_ENTITY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b([A-Z]{2,}-\d+|\d{3,}|[0-9a-f]{8}-[0-9a-f]{4})\b"
)

# High-severity markers in tags or categories
_HIGH_SEVERITY_TAGS: Final[set[str]] = {
    "security",
    "auth",
    "authorization",
    "privilege",
    "injection",
    "data_isolation",
    "critical_invariants",
    "concurrency",
    "rate_limit",
    "idor",
    "prompt_injection",
    "leakage",
}


class CandidateQualityScore(BaseModel):
    """Multi-axis quality grading for a candidate test."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    severity: float = Field(ge=0.0, le=1.0, description="Failure severity weight (0-1)")
    novelty: float = Field(ge=0.0, le=1.0, description="Uniqueness vs accepted pool (0-1)")
    flakiness_risk: float = Field(ge=0.0, le=1.0, description="Likelihood of flake or ambiguity (0-1)")
    execution_cost: float = Field(ge=0.0, le=1.0, description="Normalized execution cost (0-1)")
    composite_score: float = Field(ge=0.0, le=1.0, description="Weighted composite quality (0-1)")
    rationale: str = Field(default="", description="Reasoning for assigned quality grade")


class JevCandidateScorer:
    """Multi-axis evaluator for candidate test pool pruning and tiering."""

    def __init__(
        self,
        quality_threshold: float = 0.35,
        novelty_threshold: float = 0.20,
    ) -> None:
        self.quality_threshold = quality_threshold
        self.novelty_threshold = novelty_threshold

    def score_candidate(
        self,
        candidate: CandidateTest,
        existing_prompts: list[str] | None = None,
    ) -> CandidateQualityScore:
        """Score an individual candidate test across all 4 quality axes."""
        severity = self._compute_severity(candidate)
        novelty = self._compute_novelty(candidate.user_prompt, existing_prompts or [])
        flakiness_risk = self._compute_flakiness(candidate)
        execution_cost = self._compute_execution_cost(candidate)

        # Base composite formula: 40% severity, 30% novelty, 20% robustness, 10% efficiency
        base_quality = (
            0.40 * severity
            + 0.30 * novelty
            + 0.20 * (1.0 - flakiness_risk)
            + 0.10 * (1.0 - execution_cost)
        )

        # Duplicate suppression: exact or near-duplicate prompts suffer severe discount
        novelty_multiplier = 0.5 + 0.5 * novelty if novelty < 0.3 else 1.0

        # Slop suppression: low-severity vague tests cannot score high merely from novel words
        severity_multiplier = 0.3 + 0.7 * min(1.0, severity / 0.3) if severity < 0.3 else 1.0

        composite = round(
            max(0.0, min(1.0, base_quality * novelty_multiplier * severity_multiplier)),
            4,
        )

        rationale = (
            f"sev={severity:.2f}, nov={novelty:.2f}, flake={flakiness_risk:.2f}, "
            f"cost={execution_cost:.2f} -> Q={composite:.3f}"
        )

        return CandidateQualityScore(
            severity=severity,
            novelty=novelty,
            flakiness_risk=flakiness_risk,
            execution_cost=execution_cost,
            composite_score=composite,
            rationale=rationale,
        )

    def filter_and_rank_pool(
        self,
        pool: list[CandidateTest],
    ) -> tuple[list[CandidateTest], dict[str, CandidateQualityScore]]:
        """Filter out low-quality/duplicate tests and promote/demote priority tiers."""
        accepted: list[CandidateTest] = []
        accepted_prompts: list[str] = []
        score_map: dict[str, CandidateQualityScore] = {}

        # 1. Mandatory tests are always accepted unconditionally into P0
        for test in pool:
            if test.is_mandatory or test.mandatory_categories:
                score = self.score_candidate(test, accepted_prompts)
                score_map[test.id] = score
                # Ensure priority tier is P0_CRITICAL for all mandatory tests
                p0_test = test if test.priority_tier == PriorityTier.P0_CRITICAL else test.model_copy(
                    update={"priority_tier": PriorityTier.P0_CRITICAL}
                )
                accepted.append(p0_test)
                accepted_prompts.append(test.user_prompt)

        # 2. Score non-mandatory candidates against the pool
        for test in pool:
            if test.id in score_map:
                continue

            score = self.score_candidate(test, accepted_prompts)
            score_map[test.id] = score

            # Prune tests that fall below quality threshold or are near-duplicates
            if score.composite_score < self.quality_threshold or score.novelty < self.novelty_threshold:
                continue

            # Assign priority tier based on composite quality & severity
            updated_test = test
            if score.composite_score >= 0.75 and score.severity >= 0.70:
                if test.priority_tier != PriorityTier.P0_CRITICAL:
                    updated_test = test.model_copy(update={"priority_tier": PriorityTier.P1_RECOMMENDED})
            elif score.composite_score < 0.55:
                if test.priority_tier != PriorityTier.P0_CRITICAL:
                    updated_test = test.model_copy(update={"priority_tier": PriorityTier.P2_EXTENDED})

            accepted.append(updated_test)
            accepted_prompts.append(test.user_prompt)

        return accepted, score_map

    @staticmethod
    def _compute_severity(candidate: CandidateTest) -> float:
        """Compute severity score in range [0.0, 1.0]."""
        if candidate.is_mandatory or candidate.mandatory_categories:
            return 1.0

        tags = {t.lower() for t in candidate.coverage_tags}
        for high_tag in _HIGH_SEVERITY_TAGS:
            if any(high_tag in t for t in tags):
                return 0.85

        failure_mode = candidate.failure_mode.lower()
        if any(w in failure_mode for w in ("unauthorized", "bypass", "leak", "escalat", "crash")):
            return 0.80

        # Penalize vague or trivial prompt/expectation
        prompt_words = re.findall(r"\w+", candidate.user_prompt.lower())
        if len(prompt_words) <= 4:
            has_vague = any(p.search(candidate.user_prompt) for p in _VAGUE_PATTERNS)
            if has_vague:
                return 0.10

        if candidate.category.lower() in ("security", "safety", "reliability"):
            return 0.75

        return 0.65

    @staticmethod
    def _compute_novelty(prompt: str, existing_prompts: list[str]) -> float:
        """Compute token-level Jaccard uniqueness in range [0.0, 1.0]."""
        if not existing_prompts:
            return 1.0

        tokens = set(re.findall(r"\w+", prompt.lower()))
        if not tokens:
            return 0.0

        max_similarity = 0.0
        for existing in existing_prompts:
            exist_tokens = set(re.findall(r"\w+", existing.lower()))
            if not exist_tokens:
                continue
            intersection = len(tokens & exist_tokens)
            union = len(tokens | exist_tokens)
            similarity = intersection / union if union > 0 else 0.0
            if similarity > max_similarity:
                max_similarity = similarity
                if max_similarity >= 0.99:
                    break

        return round(max(0.0, min(1.0, 1.0 - max_similarity)), 4)

    @staticmethod
    def _compute_flakiness(candidate: CandidateTest) -> float:
        """Compute flakiness risk in range [0.0, 1.0]."""
        risk = 0.10  # default low base flakiness

        # Check for vague phrasing in prompt or expected behavior
        for pattern in _VAGUE_PATTERNS:
            if pattern.search(candidate.user_prompt):
                risk += 0.40
            if pattern.search(candidate.expected_behavior):
                risk += 0.30

        # Check for presence of concrete test entities/fixtures
        has_entity = bool(_CONCRETE_ENTITY_PATTERN.search(candidate.user_prompt))
        if not has_entity:
            prompt_tokens = re.findall(r"\w+", candidate.user_prompt)
            if len(prompt_tokens) < 5:
                risk += 0.25

        # Check length of expected behavior
        if len(candidate.expected_behavior.strip()) < 10:
            risk += 0.20

        return round(max(0.0, min(1.0, risk)), 4)

    @staticmethod
    def _compute_execution_cost(candidate: CandidateTest) -> float:
        """Compute normalized execution cost in range [0.0, 1.0]."""
        # Baseline execution cost from model + text length penalty
        text_len = len(candidate.user_prompt) + len(candidate.expected_behavior)
        length_penalty = min(0.4, text_len / 1000.0)
        base_cost = min(0.6, candidate.execution_cost / 10.0)
        return round(max(0.05, min(1.0, base_cost + length_penalty)), 4)
