"""Suite run verdict diff."""

from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult
from agenteval.planning.run_diff import VerdictChangeKind, diff_suite_runs


def make_case_result(test_id: str, verdict: str) -> TestCaseResult:
    return TestCaseResult(
        test_id=test_id,
        verdict=verdict,
        observation=ObservationBundle(test_id=test_id, user_prompt="p", response_text="r"),
        rationale="",
    )


def test_diff_detects_regression_and_fix() -> None:
    baseline = SuiteRunReport(
        agent_id="a",
        run_id="run1",
        suite_version=1,
        results=[
            make_case_result("t1", "PASS"),
            make_case_result("t2", "FAIL"),
        ],
        passed=1,
        failed=1,
        unverifiable=0,
    )
    current = SuiteRunReport(
        agent_id="a",
        run_id="run2",
        suite_version=1,
        results=[
            make_case_result("t1", "FAIL"),
            make_case_result("t2", "PASS"),
        ],
        passed=1,
        failed=1,
        unverifiable=0,
    )
    diff = diff_suite_runs(baseline, current)
    assert diff is not None
    by_id = {c.test_id: c for c in diff.changes}
    assert by_id["t1"].kind == VerdictChangeKind.REGRESSED
    assert by_id["t2"].kind == VerdictChangeKind.FIXED
    assert len(diff.regressions) == 1
    assert len(diff.fixes) == 1


def test_diff_skips_different_suite_versions() -> None:
    baseline = SuiteRunReport(agent_id="a", run_id="r1", suite_version=1)
    current = SuiteRunReport(agent_id="a", run_id="r2", suite_version=2)
    assert diff_suite_runs(baseline, current) is None
