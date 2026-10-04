"""Tests for Slice 7: Incremental Run Persistence (Streaming Flushes & Crash Recovery)."""

import concurrent.futures
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from agenteval.db.suite_repository import SuiteRepository
from agenteval.planning.execution_trace import build_blackbox_trajectory
from agenteval.planning.models import (
    CandidateTest,
    ObservationBundle,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.planning.suite_store import SuiteStore
from agenteval.services.suite_workflow import SuiteWorkflow


def _create_sample_suite(
    db_path: Path, agent_id: str = "inc-agent", test_count: int = 3
) -> SuiteRepository:
    repo = SuiteRepository(db_path)
    tests = [
        CandidateTest(
            id=f"t{i}",
            capability_id="cap",
            persona_id="p1",
            name=f"Test {i}",
            user_prompt=f"prompt {i}",
            expected_behavior=f"behavior {i}",
        )
        for i in range(1, test_count + 1)
    ]
    pack = TestPack(
        agent_id=agent_id,
        version=1,
        tests=tests,
        candidate_count=test_count,
        requirements_fingerprint="fp1",
    )
    manifest = SuiteStore.new_manifest(agent_id, "fp1", "http://127.0.0.1/chat")
    repo.init_suite(manifest, tests, pack)
    return repo


def test_incremental_lifecycle_and_live_tallies(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    agent_id = "inc-agent"
    repo = _create_sample_suite(db, agent_id=agent_id, test_count=3)

    run_id = "run-inc-1"
    repo.initialize_run(agent_id, run_id, 1, endpoint_url="http://127.0.0.1/chat")

    record = repo.get_run_record(run_id)
    assert record is not None
    assert record["status"] == "running"
    assert record["passed"] == 0
    assert record["failed"] == 0
    assert record["unverifiable"] == 0

    # Ensure in-flight run is not surfaced as latest completed baseline
    assert repo.load_latest_run(agent_id) is None

    # Flush 1: PASS
    obs1 = ObservationBundle(
        test_id="t1",
        user_prompt="prompt 1",
        response_text="Hello",
        http_status=200,
        raw_json={"thought": "thinking step 1"},
    )
    traj1 = build_blackbox_trajectory(
        observation=obs1,
        verdict="PASS",
        rationale="Passed successfully",
    )
    res1 = TestCaseResult(
        test_id="t1",
        verdict="PASS",
        observation=obs1,
        rationale="Passed successfully",
        trajectory=traj1,
    )
    repo.save_partial_result(run_id, res1)

    record = repo.get_run_record(run_id)
    assert record is not None
    assert record["status"] == "running"
    assert record["passed"] == 1
    assert record["failed"] == 0

    # Flush 2: FAIL
    obs2 = ObservationBundle(
        test_id="t2",
        user_prompt="prompt 2",
        response_text="Error 500",
        http_status=500,
    )
    traj2 = build_blackbox_trajectory(
        observation=obs2,
        verdict="FAIL",
        rationale="Failed response",
    )
    res2 = TestCaseResult(
        test_id="t2",
        verdict="FAIL",
        observation=obs2,
        rationale="Failed response",
        trajectory=traj2,
    )
    repo.save_partial_result(run_id, res2)

    record = repo.get_run_record(run_id)
    assert record is not None
    assert record["passed"] == 1
    assert record["failed"] == 1
    assert record["unverifiable"] == 0

    # Flush 3: UNVERIFIABLE
    obs3 = ObservationBundle(
        test_id="t3",
        user_prompt="prompt 3",
        response_text="Timeout",
        http_status=504,
    )
    res3 = TestCaseResult(
        test_id="t3",
        verdict="UNVERIFIABLE",
        observation=obs3,
        rationale="Unverifiable execution",
    )
    repo.save_partial_result(run_id, res3)

    record = repo.get_run_record(run_id)
    assert record is not None
    assert record["passed"] == 1
    assert record["failed"] == 1
    assert record["unverifiable"] == 1

    # Finalize
    report = SuiteRunReport(
        agent_id=agent_id,
        run_id=run_id,
        suite_version=1,
        results=[res1, res2, res3],
        passed=1,
        failed=1,
        unverifiable=1,
    )
    repo.finalize_run(agent_id, report, endpoint_url="http://127.0.0.1/chat")

    record = repo.get_run_record(run_id)
    assert record is not None
    assert record["status"] == "completed"

    # Now load_latest_run succeeds
    latest = repo.load_latest_run(agent_id)
    assert latest is not None
    assert latest.run_id == run_id
    assert latest.status == "completed"
    assert len(latest.results) == 3


def test_crash_recovery_preserves_partial_results_and_trajectories(tmp_path: Path) -> None:
    db = tmp_path / "crash.db"
    agent_id = "crash-agent"
    repo = _create_sample_suite(db, agent_id=agent_id, test_count=3)

    run_id = "run-crash-99"
    repo.initialize_run(agent_id, run_id, 1, endpoint_url="http://127.0.0.1/chat")

    # Complete test 1 and 2
    obs1 = ObservationBundle(
        test_id="t1",
        user_prompt="step 1 prompt",
        response_text="step 1 done",
        http_status=200,
        raw_json={"thought": "analysis"},
    )
    traj1 = build_blackbox_trajectory(
        observation=obs1,
        verdict="PASS",
        rationale="T1 passed",
    )
    res1 = TestCaseResult(
        test_id="t1",
        verdict="PASS",
        observation=obs1,
        rationale="T1 passed",
        trajectory=traj1,
    )
    repo.save_partial_result(run_id, res1)

    obs2 = ObservationBundle(
        test_id="t2",
        user_prompt="step 2 prompt",
        response_text="step 2 fail",
        http_status=400,
    )
    traj2 = build_blackbox_trajectory(
        observation=obs2,
        verdict="FAIL",
        rationale="T2 failed",
    )
    res2 = TestCaseResult(
        test_id="t2",
        verdict="FAIL",
        observation=obs2,
        rationale="T2 failed",
        trajectory=traj2,
    )
    repo.save_partial_result(run_id, res2)

    # Simulate unexpected failure (SIGTERM, container preemption, unhandled exception)
    repo.mark_run_failed(run_id, "Container preempted by Cloud Run autoscaler")

    record = repo.get_run_record(run_id)
    assert record is not None
    assert record["status"] == "failed"
    assert record["error_message"] == "Container preempted by Cloud Run autoscaler"

    # Load partial results from failed run
    loaded_report = repo.load_run(agent_id, run_id)
    assert loaded_report is not None
    assert loaded_report.status == "failed"
    assert loaded_report.error == "Container preempted by Cloud Run autoscaler"
    assert len(loaded_report.results) == 2
    assert loaded_report.passed == 1
    assert loaded_report.failed == 1

    # Verify trajectories survived the crash
    assert len(loaded_report.results[0].trajectory) > 0
    assert loaded_report.results[0].trajectory[0].kind == "user_message"

    # Ensure failed run is NOT returned as latest baseline
    assert repo.load_latest_run(agent_id) is None


def test_concurrent_streaming_flushes_thread_safety(tmp_path: Path) -> None:
    db = tmp_path / "concurrent.db"
    agent_id = "conc-agent"
    test_count = 20
    repo = _create_sample_suite(db, agent_id=agent_id, test_count=test_count)

    run_id = "run-concurrent"
    repo.initialize_run(agent_id, run_id, 1, endpoint_url="http://127.0.0.1/chat")

    results_to_save: list[TestCaseResult] = []
    for i in range(1, test_count + 1):
        verdict = "PASS" if i % 2 == 0 else "FAIL"
        obs = ObservationBundle(
            test_id=f"t{i}",
            user_prompt=f"p {i}",
            response_text=f"Out {i}",
            http_status=200,
        )
        results_to_save.append(
            TestCaseResult(
                test_id=f"t{i}",
                verdict=verdict,
                observation=obs,
                rationale=f"Result {i}",
                trajectory=build_blackbox_trajectory(
                    observation=obs,
                    verdict=verdict,
                    rationale=f"Result {i}",
                ),
            )
        )

    # 10 worker threads writing partial results simultaneously
    def _worker(res: TestCaseResult) -> None:
        repo.save_partial_result(run_id, res)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_worker, r) for r in results_to_save]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    record = repo.get_run_record(run_id)
    assert record is not None
    assert record["passed"] == 10
    assert record["failed"] == 10
    assert record["unverifiable"] == 0

    loaded = repo.load_run(agent_id, run_id)
    assert loaded is not None
    assert len(loaded.results) == 20


def test_suite_workflow_streaming_and_failure_handling(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow_test.db"
    workflow = SuiteWorkflow(
        suite_root=str(tmp_path / "suites"),
        use_sqlite=True,
        db_path=db_path,
    )
    repo = _create_sample_suite(db_path, agent_id="wf-agent", test_count=2)

    # Patch runner to simulate mid-run crash after first test
    with patch("agenteval.services.suite_workflow.BlackboxRunner") as mock_runner_cls:
        mock_runner = MagicMock()

        def _fake_run_pack(
            pack: TestPack,
            run_id: str | None = None,
            max_workers: int | None = None,
            on_progress: Any = None,
            on_result: Any = None,
        ) -> SuiteRunReport:
            # Stream one result
            res = TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=ObservationBundle(
                    test_id="t1",
                    user_prompt="prompt 1",
                    response_text="OK",
                    http_status=200,
                ),
            )
            if on_result:
                on_result(res)
            # Raise unhandled error
            raise RuntimeError("Out of memory on worker node")

        mock_runner.run_pack.side_effect = _fake_run_pack
        mock_runner_cls.return_value = mock_runner

        run_id = "wf-run-fail"
        try:
            workflow.run_suite("wf-agent", run_id=run_id, endpoint_url="http://127.0.0.1/chat")
            raise AssertionError("Expected RuntimeError")
        except RuntimeError as e:
            assert "Out of memory" in str(e)

        # Verify run row is marked as failed and first result was preserved
        record = repo.get_run_record(run_id)
        assert record is not None
        assert record["status"] == "failed"
        assert "Out of memory" in str(record["error_message"])

        loaded = repo.load_run("wf-agent", run_id)
        assert loaded is not None
        assert loaded.status == "failed"
        assert len(loaded.results) == 1
        assert loaded.results[0].test_id == "t1"
