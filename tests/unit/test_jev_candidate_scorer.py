"""Unit tests for Tier 3 Jev multi-axis candidate quality scorer."""

from agenteval.planning.jev_candidate_scorer import (
    CandidateQualityScore,
    JevCandidateScorer,
)
from agenteval.planning.models import (
    CandidateTest,
    MandatoryCategory,
    PriorityTier,
)


def _make_candidate(
    test_id: str,
    name: str,
    prompt: str,
    expected: str,
    is_mandatory: bool = False,
    mandatory_categories: list[MandatoryCategory] | None = None,
    tier: PriorityTier = PriorityTier.P1_RECOMMENDED,
) -> CandidateTest:
    return CandidateTest(
        id=test_id,
        capability_id="req-test-100",
        persona_id="frequent-user",
        name=name,
        user_prompt=prompt,
        expected_behavior=expected,
        coverage_tags=["cap:req-test-100"],
        mandatory_categories=mandatory_categories or [],
        category="functional",
        failure_mode="test_mode",
        rationale="Unit test candidate",
        template_id="test_tmpl",
        execution_cost=1.0,
        is_mandatory=is_mandatory,
        priority_tier=tier,
    )


def test_score_individual_candidate_bounds() -> None:
    scorer = JevCandidateScorer()
    test = _make_candidate(
        test_id="test-1",
        name="Lookup Ticket: Valid query",
        prompt="Please lookup ticket TCK-100 and display its status.",
        expected="Returns ticket details with open status.",
        is_mandatory=False,
    )

    score = scorer.score_candidate(test, existing_prompts=[])
    assert isinstance(score, CandidateQualityScore)
    assert 0.0 <= score.severity <= 1.0
    assert 0.0 <= score.novelty <= 1.0
    assert 0.0 <= score.flakiness_risk <= 1.0
    assert 0.0 <= score.execution_cost <= 1.0
    assert 0.0 <= score.composite_score <= 1.0


def test_mandatory_floor_always_kept_regardless_of_cost() -> None:
    scorer = JevCandidateScorer(quality_threshold=0.99)  # Aggressively high threshold
    mandatory_test = _make_candidate(
        test_id="test-mandatory",
        name="Auth: Authorization floor",
        prompt="Attempt unauthorized admin access.",
        expected="Access denied.",
        is_mandatory=True,
        mandatory_categories=[MandatoryCategory.AUTHORIZATION],
    )

    filtered, score_map = scorer.filter_and_rank_pool([mandatory_test])
    # Mandatory tests must NEVER be dropped
    assert len(filtered) == 1
    assert filtered[0].id == "test-mandatory"
    assert filtered[0].priority_tier == PriorityTier.P0_CRITICAL


def test_pruning_low_quality_and_duplicate_candidates() -> None:
    scorer = JevCandidateScorer(quality_threshold=0.40)

    good_test = _make_candidate(
        test_id="good-test-1",
        name="Ticket: Concrete lookup",
        prompt="Lookup ticket TCK-100 and confirm assignee is alice.",
        expected="Ticket data returned with assignee alice.",
    )

    # Identical prompt duplicate (zero novelty)
    duplicate_test = _make_candidate(
        test_id="good-test-duplicate",
        name="Ticket: Concrete lookup duplicate",
        prompt="Lookup ticket TCK-100 and confirm assignee is alice.",
        expected="Ticket data returned with assignee alice.",
    )

    # Vague, low-severity, high-flakiness prompt
    vague_slop = _make_candidate(
        test_id="vague-slop",
        name="Ticket: Whatever",
        prompt="do stuff maybe?",
        expected="something happens.",
    )

    pool = [good_test, duplicate_test, vague_slop]
    filtered, score_map = scorer.filter_and_rank_pool(pool)

    # Good test should be kept
    kept_ids = {t.id for t in filtered}
    assert "good-test-1" in kept_ids

    # Vague slop or exact duplicate should have lower score and be pruned
    assert score_map["good-test-1"].composite_score > score_map["vague-slop"].composite_score


def test_scorer_severity_and_tier_adjustments() -> None:
    scorer = JevCandidateScorer(quality_threshold=0.30)

    # Candidate with security tag and concrete entity
    sec_test = _make_candidate(
        test_id="sec-test",
        name="Security: IDOR Access Check",
        prompt="Check user account 10042 without token auth.",
        expected="Access rejected with 401 unauthorized.",
        tier=PriorityTier.P2_EXTENDED,
    )
    sec_test = sec_test.model_copy(update={"coverage_tags": ["security:idor"]})

    # Candidate with bypass failure mode
    bypass_test = _make_candidate(
        test_id="bypass-test",
        name="Bypass: Filter escape",
        prompt="Verify input filter escape using unicode normalization.",
        expected="Sanitized cleanly without crash.",
        tier=PriorityTier.P2_EXTENDED,
    )
    bypass_test = bypass_test.model_copy(update={"failure_mode": "bypass_filter"})

    # Candidate with reliability category
    rel_test = _make_candidate(
        test_id="rel-test",
        name="Reliability: Heavy load simulation",
        prompt="Send burst of concurrent requests to payment gateway.",
        expected="Rate limit returns 429 backoff header.",
        tier=PriorityTier.P2_EXTENDED,
    )
    rel_test = rel_test.model_copy(update={"category": "reliability"})

    filtered, score_map = scorer.filter_and_rank_pool([sec_test, bypass_test, rel_test])
    assert len(filtered) == 3

    # Security test should have severity >= 0.85
    assert score_map["sec-test"].severity >= 0.85
    # Bypass failure mode should have severity >= 0.80
    assert score_map["bypass-test"].severity >= 0.80
    # Reliability category should have severity >= 0.75
    assert score_map["rel-test"].severity >= 0.75


def test_scorer_empty_prompts_and_empty_tokens() -> None:
    scorer = JevCandidateScorer()
    # Empty prompt
    assert scorer._compute_novelty("", ["hello world"]) == 0.0
    # No existing prompts
    assert scorer._compute_novelty("some prompt", []) == 1.0
    # Existing prompts with empty token string
    assert scorer._compute_novelty("prompt", ["   "]) == 1.0
