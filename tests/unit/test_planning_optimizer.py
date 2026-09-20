"""Unit tests for test pack optimizer and coverage mapper (B0, B4, B5)."""

from agenteval.planning.coverage import CoverageMapper
from agenteval.planning.models import CandidateTest, MandatoryCategory, OptimizerConfig
from agenteval.planning.optimizer import TestPackOptimizer


def _candidate(
    test_id: str,
    cap: str,
    persona: str,
    tags: list[str],
    mandatory: list[MandatoryCategory] | None = None,
    *,
    is_mandatory: bool = False,
    cost: float = 1.0,
) -> CandidateTest:
    return CandidateTest(
        id=test_id,
        capability_id=cap,
        persona_id=persona,
        name=test_id,
        user_prompt=f"prompt for {test_id}",
        expected_behavior="observable outcome",
        coverage_tags=tags,
        mandatory_categories=mandatory or [],
        category="security" if mandatory else "functional",
        failure_mode="hypothesis",
        rationale="fixture",
        execution_cost=cost,
        is_mandatory=is_mandatory,
    )


def test_optimizer_reduces_pool_and_keeps_mandatory_security() -> None:
    """Large pool collapses to max_tests while retaining auth and injection floors."""
    pool: list[CandidateTest] = []
    for i in range(20):
        pool.append(
            _candidate(
                f"happy-{i}",
                "order",
                "frequent",
                [f"cap:order", f"persona:frequent", f"failure:happy_{i % 3}"],
            )
        )
    pool.append(
        _candidate(
            "sec-auth",
            "order",
            "auditor",
            ["cap:order", "persona:auditor", "security:auth"],
            [MandatoryCategory.AUTHORIZATION],
        )
    )
    pool.append(
        _candidate(
            "sec-inject",
            "order",
            "adversary",
            ["cap:order", "persona:adversary", "security:injection"],
            [MandatoryCategory.PROMPT_INJECTION],
        )
    )

    config = OptimizerConfig(
        max_tests=8,
        applicable_mandatory=[
            MandatoryCategory.AUTHORIZATION,
            MandatoryCategory.PROMPT_INJECTION,
        ],
    )
    result = TestPackOptimizer().optimize("agent-order", pool, config)
    assert result.pack.candidate_count == 22
    assert len(result.pack.tests) <= 8
    assert MandatoryCategory.AUTHORIZATION in result.mandatory_satisfied
    assert MandatoryCategory.PROMPT_INJECTION in result.mandatory_satisfied
    assert result.removed_as_redundant == 22 - len(result.pack.tests)
    ids = {t.id for t in result.pack.tests}
    assert "sec-auth" in ids
    assert "sec-inject" in ids


def test_optimizer_drops_redundant_happy_paths() -> None:
    """Greedy cover should not select all duplicate happy-path variants."""
    pool = [
        _candidate("h1", "refund", "user", ["cap:refund", "failure:happy"]),
        _candidate("h2", "refund", "user", ["cap:refund", "failure:happy"]),
        _candidate("h3", "refund", "user", ["cap:refund", "failure:happy"]),
        _candidate("edge", "refund", "user", ["cap:refund", "failure:invalid"]),
    ]
    config = OptimizerConfig(max_tests=2, applicable_mandatory=[])
    result = TestPackOptimizer().optimize("agent-refund", pool, config)
    assert len(result.pack.tests) == 2
    tags = {tag for t in result.pack.tests for tag in t.coverage_tags}
    assert "failure:invalid" in tags


def test_coverage_report_critical_uncovered_mandatory() -> None:
    """Coverage flags missing mandatory category and uncovered security tags."""
    pool = [
        _candidate(
            "only-happy",
            "pay",
            "user",
            ["cap:pay", "security:auth"],
            [MandatoryCategory.AUTHORIZATION],
        ),
        _candidate(
            "inject",
            "pay",
            "adv",
            ["cap:pay", "security:injection"],
            [MandatoryCategory.PROMPT_INJECTION],
        ),
    ]
    selected = [pool[0]]
    report = CoverageMapper().report(
        pool,
        selected,
        applicable_mandatory=[
            MandatoryCategory.AUTHORIZATION,
            MandatoryCategory.PROMPT_INJECTION,
        ],
    )
    assert "mandatory:prompt_injection" in report.critical_uncovered
    assert "security:injection" in report.uncovered_tags
    assert report.axes.get("cap", 0) == 1.0
