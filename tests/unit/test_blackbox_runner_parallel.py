"""Unit tests verifying parallel test execution, deterministic ordering, and error isolation (Slice 4)."""

import time
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from agenteval.planning.blackbox_runner import BlackboxRunner, JudgeMode
from agenteval.planning.models import (
    CandidateTest,
    ObservationBundle,
    TestPack,
)


def _make_candidate_test(test_id: str, prompt: str = "Test prompt") -> CandidateTest:
    return CandidateTest(
        id=test_id,
        name=f"Test {test_id}",
        capability_id="cap-001",
        persona_id="persona-default",
        user_prompt=prompt,
        expected_behavior="Expected response",
        category="security",
    )


def test_blackbox_runner_parallel_speedup_and_deterministic_order() -> None:
    """Verify that multiple tests run concurrently and results preserve canonical order."""
    tests = [_make_candidate_test(f"test-{i}") for i in range(8)]
    pack = TestPack(
        agent_id="test-agent",
        version=1,
        tests=tests,
        candidate_count=len(tests),
    )

    # Mock _invoke with varying simulated network delays
    # Even if test-0 takes longest (0.06s) and test-7 finishes first (0.01s),
    # results must remain sorted [test-0, test-1, ..., test-7].
    def delayed_invoke(test: CandidateTest) -> ObservationBundle:
        idx = int(test.id.split("-")[1])
        # Invert delay: earlier tests sleep longer
        sleep_time = (8 - idx) * 0.008
        time.sleep(sleep_time)
        return ObservationBundle(
            test_id=test.id,
            user_prompt=test.user_prompt,
            response_text="Refund processed successfully",
            http_status=200,
            latency_ms=sleep_time * 1000,
            raw_json={"reply": "Refund processed successfully"},
        )

    runner = BlackboxRunner(
        endpoint_url="http://agent.test.local/chat",
        allow_private=True,
        judge_mode=JudgeMode.DETERMINISTIC_ONLY,
    )

    with patch.object(runner, "_invoke", side_effect=delayed_invoke):
        start = time.perf_counter()
        report = runner.run_pack(pack, max_workers=8)
        elapsed = time.perf_counter() - start

    # If sequential, sum of sleep_time is ~0.288s. Parallel with 8 workers takes ~0.064s.
    assert elapsed < 0.20, f"Parallel execution took too long: {elapsed:.3f}s"
    assert len(report.results) == 8
    # Assert deterministic ordering matching original pack
    result_ids = [r.test_id for r in report.results]
    expected_ids = [t.id for t in tests]
    assert result_ids == expected_ids


def test_blackbox_runner_sequential_fallback() -> None:
    """Verify max_workers=1 executes sequentially without thread pool errors."""
    tests = [_make_candidate_test(f"test-{i}") for i in range(3)]
    pack = TestPack(agent_id="test-agent", version=1, tests=tests, candidate_count=len(tests))

    runner = BlackboxRunner(
        endpoint_url="http://agent.test.local/chat",
        allow_private=True,
        max_workers=1,
    )

    mock_obs = ObservationBundle(
        test_id="any",
        user_prompt="prompt",
        response_text="cannot fulfill request",
        http_status=200,
        latency_ms=10.0,
        raw_json={"reply": "cannot fulfill request"},
    )

    with patch.object(runner, "_invoke", return_value=mock_obs):
        report = runner.run_pack(pack, max_workers=1)

    assert len(report.results) == 3
    assert [r.test_id for r in report.results] == ["test-0", "test-1", "test-2"]


def test_blackbox_runner_exception_containment() -> None:
    """Verify that an unexpected exception in one test does not crash the entire suite."""
    tests = [_make_candidate_test(f"test-{i}") for i in range(4)]
    pack = TestPack(agent_id="test-agent", version=1, tests=tests, candidate_count=len(tests))

    def flaky_invoke(test: CandidateTest) -> ObservationBundle:
        if test.id == "test-2":
            raise RuntimeError("Simulated network kernel panic")
        return ObservationBundle(
            test_id=test.id,
            user_prompt=test.user_prompt,
            response_text="cannot fulfill request",
            http_status=200,
            latency_ms=10.0,
            raw_json={"reply": "cannot fulfill request"},
        )

    runner = BlackboxRunner(
        endpoint_url="http://agent.test.local/chat",
        allow_private=True,
        judge_mode=JudgeMode.DETERMINISTIC_ONLY,
    )

    with patch.object(runner, "_invoke", side_effect=flaky_invoke):
        report = runner.run_pack(pack, max_workers=4)

    assert len(report.results) == 4
    # test-2 must be caught and returned as UNVERIFIABLE
    failed_test = next(r for r in report.results if r.test_id == "test-2")
    assert failed_test.verdict == "UNVERIFIABLE"
    assert "Simulated network kernel panic" in failed_test.rationale
    assert failed_test.trajectory is not None
    # Other tests must succeed normally
    normal_tests = [r for r in report.results if r.test_id != "test-2"]
    assert len(normal_tests) == 3
    assert all(r.verdict == "PASS" for r in normal_tests)


def test_blackbox_runner_env_var_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify AGENTEVAL_MAX_CONCURRENT_TESTS environment variable is respected."""
    monkeypatch.setenv("AGENTEVAL_MAX_CONCURRENT_TESTS", "12")
    runner = BlackboxRunner(endpoint_url="http://agent.test.local/chat", allow_private=True)
    assert runner.max_workers == 12

    # Verify bounds capping
    monkeypatch.setenv("AGENTEVAL_MAX_CONCURRENT_TESTS", "999")
    runner_capped = BlackboxRunner(endpoint_url="http://agent.test.local/chat", allow_private=True)
    assert runner_capped.max_workers == 50

    monkeypatch.setenv("AGENTEVAL_MAX_CONCURRENT_TESTS", "0")
    runner_floored = BlackboxRunner(endpoint_url="http://agent.test.local/chat", allow_private=True)
    assert runner_floored.max_workers == 1


def test_suite_run_request_schema_concurrency() -> None:
    """Verify SuiteRunRequest accepts and validates max_concurrency."""
    from agenteval.api.schemas import SuiteRunRequest

    req = SuiteRunRequest(max_concurrency=16)
    assert req.max_concurrency == 16

    # Verify ge=1 and le=50 bounds validation
    with pytest.raises(ValidationError):
        SuiteRunRequest(max_concurrency=0)

    with pytest.raises(ValidationError):
        SuiteRunRequest(max_concurrency=100)

