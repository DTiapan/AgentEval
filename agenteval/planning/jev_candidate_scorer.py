"""Tier 3 TypeSafe AI / Jev multi-axis candidate quality filter and scorer.

Evaluates synthesized candidate tests across 4 dimensions before set-cover optimization:
1. Severity: Impact of failure (critical floor vs minor formatting).
2. Novelty: Linguistic & semantic uniqueness against the current candidate pool.
3. Flakiness Risk: Ambiguity, non-deterministic phrasing, or missing assertions.
4. Execution Cost: Relative token length and tool execution overhead.

Integrates TypeSafe AI's Jev model (System One structured decision engine)
via typesafe-sdk (Choice, Noul, Score) with a 100% deterministic local
calibrated fallback for air-gapped CI and offline execution.
"""

from __future__ import annotations

import os
import re
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

from agenteval.planning._utils import load_env
from agenteval.planning.models import (
    CandidateTest,
    PriorityTier,
)

load_env()

try:
    from typesafe_sdk import Choice, Noul, TypeSafeClient

    _TYPESAFE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TYPESAFE_AVAILABLE = False

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
    recommended_tier: PriorityTier = Field(
        default=PriorityTier.P1_RECOMMENDED,
        description="Recommended priority tier from Jev",
    )
    source: str = Field(
        default="local_heuristic",
        description="Classifier origin (typesafe_jev, local_heuristic, local_heuristic_fallback)",
    )
    rationale: str = Field(default="", description="Reasoning for assigned quality grade")


class JevCandidateScorer:
    """TypeSafe AI / Jev powered evaluator for candidate test pool pruning and tiering."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        quality_threshold: float = 0.35,
        novelty_threshold: float = 0.20,
        timeout: float = 5.0,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY") or os.getenv("JEV_API_KEY")
        self.model = model or os.getenv("TYPESAFE_DEFAULT_MODEL")
        self.base_url = base_url or os.getenv("TYPESAFE_BASE_URL")
        self.quality_threshold = quality_threshold
        self.novelty_threshold = novelty_threshold
        self.timeout = timeout
        self._client: Any = client

        if self._client is None and self.api_key and _TYPESAFE_AVAILABLE:
            try:
                self._client = TypeSafeClient(
                    api_key=self.api_key,
                    model=self.model,
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
            except Exception:  # pragma: no cover
                self._client = None

    def score_candidate(
        self,
        candidate: CandidateTest,
        existing_prompts: list[str] | None = None,
    ) -> CandidateQualityScore:
        """Score an individual candidate test across all 4 quality axes using TypeSafe AI Jev or fallback."""
        if self._client is not None and _TYPESAFE_AVAILABLE:
            try:
                return self._typesafe_jev_score(candidate, existing_prompts)
            except Exception:
                return self._local_heuristic_score(
                    candidate, existing_prompts, source="local_heuristic_fallback"
                )

        return self._local_heuristic_score(
            candidate, existing_prompts, source="local_heuristic"
        )

    def _typesafe_jev_score(
        self,
        candidate: CandidateTest,
        existing_prompts: list[str] | None = None,
    ) -> CandidateQualityScore:
        """Evaluate candidate with TypeSafe AI's Jev System One model."""
        state = {
            "name": candidate.name,
            "user_prompt": candidate.user_prompt,
            "expected_behavior": candidate.expected_behavior,
            "category": candidate.category,
            "failure_mode": candidate.failure_mode,
            "rationale": candidate.rationale,
            "is_mandatory": candidate.is_mandatory,
            "mandatory_categories": [m.value for m in candidate.mandatory_categories],
        }

        questions = {
            "include_in_suite": Noul(
                instructions="Should this test case be included in the production assurance test suite? High-value boundary, security, or core workflow tests should be included (1.0), while vague slop or duplicates should not (0.0)."
            ),
            "priority_tier": Choice(
                instructions="Which priority tier should this test be classified into?",
                criteria={"P0": None, "P1": None, "P2": None},
            ),
            "severity": Choice(
                instructions="What is the failure impact severity of this test?",
                criteria={"critical": None, "high": None, "medium": None, "low": None},
            ),
            "flakiness_risk": Choice(
                instructions="What is the flakiness or ambiguity risk of this test prompt?",
                criteria={"low": None, "medium": None, "high": None},
            ),
        }

        res = self._client.system_one(state=state, questions=questions)
        composite = float(res.nouls["include_in_suite"].noul)

        sev_choice = res.choices["severity"].choice
        severity_map = {"critical": 1.0, "high": 0.85, "medium": 0.65, "low": 0.30}
        severity = severity_map.get(sev_choice, 0.65)

        flake_choice = res.choices["flakiness_risk"].choice
        flake_map = {"high": 0.85, "medium": 0.40, "low": 0.10}
        flakiness_risk = flake_map.get(flake_choice, 0.10)

        tier_choice = res.choices["priority_tier"].choice
        tier_map = {
            "P0": PriorityTier.P0_CRITICAL,
            "P1": PriorityTier.P1_RECOMMENDED,
            "P2": PriorityTier.P2_EXTENDED,
        }
        rec_tier = tier_map.get(tier_choice, PriorityTier.P1_RECOMMENDED)

        novelty = self._compute_novelty(candidate.user_prompt, existing_prompts or [])
        execution_cost = self._compute_execution_cost(candidate)

        if novelty < 0.3:
            composite = round(composite * (0.5 + 0.5 * novelty), 4)

        composite_clamped = round(max(0.0, min(1.0, composite)), 4)
        rationale = (
            f"TypeSafe Jev System One: Q={composite_clamped:.2f}, tier={rec_tier.value}, "
            f"sev={sev_choice}, flake={flake_choice}"
        )

        return CandidateQualityScore(
            severity=severity,
            novelty=novelty,
            flakiness_risk=flakiness_risk,
            execution_cost=execution_cost,
            composite_score=composite_clamped,
            recommended_tier=rec_tier,
            source="typesafe_jev",
            rationale=rationale,
        )

    def _local_heuristic_score(
        self,
        candidate: CandidateTest,
        existing_prompts: list[str] | None = None,
        source: str = "local_heuristic",
    ) -> CandidateQualityScore:
        """Deterministic local scoring fallback when running in air-gapped CI or offline environments."""
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

        # Recommended tier from heuristic
        if candidate.is_mandatory or candidate.mandatory_categories or severity >= 0.95:
            rec_tier = PriorityTier.P0_CRITICAL
        elif composite >= 0.70 and severity >= 0.65:
            rec_tier = PriorityTier.P1_RECOMMENDED
        else:
            rec_tier = PriorityTier.P2_EXTENDED

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
            recommended_tier=rec_tier,
            source=source,
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

            # Assign priority tier based on Jev recommendations
            updated_test = test
            if score.recommended_tier == PriorityTier.P0_CRITICAL and test.priority_tier != PriorityTier.P0_CRITICAL:
                # Do not promote non-mandatory tests to P0 unless explicitly mandatory
                updated_test = test.model_copy(update={"priority_tier": PriorityTier.P1_RECOMMENDED})
            elif score.recommended_tier == PriorityTier.P1_RECOMMENDED and test.priority_tier != PriorityTier.P0_CRITICAL:
                updated_test = test.model_copy(update={"priority_tier": PriorityTier.P1_RECOMMENDED})
            elif score.recommended_tier == PriorityTier.P2_EXTENDED and test.priority_tier != PriorityTier.P0_CRITICAL:
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
        text_len = len(candidate.user_prompt) + len(candidate.expected_behavior)
        length_penalty = min(0.4, text_len / 1000.0)
        base_cost = min(0.6, candidate.execution_cost / 10.0)
        return round(max(0.05, min(1.0, base_cost + length_penalty)), 4)
