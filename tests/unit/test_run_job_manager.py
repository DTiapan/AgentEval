"""Unit tests for in-process asynchronous RunJobManager (Slice 6)."""

import time
from unittest.mock import MagicMock

from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult
from agenteval.services.run_manager import JobStatus, RunJobManager, get_run_job_manager


def test_singleton_run_job_manager() -> None:
    mgr1 = get_run_job_manager()
    mgr2 = get_run_job_manager()
    assert mgr1 is mgr2


def test_run_job_manager_success_lifecycle() -> None:
    manager = RunJobManager(max_concurrent_jobs=2)
    workflow_mock = MagicMock()

    dummy_report = SuiteRunReport(
        agent_id="test-agent",
        run_id="run-123",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=ObservationBundle(test_id="t1", user_prompt="p", response_text="r"),
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )

    def fake_run_suite(*args: object, **kwargs: object) -> SuiteRunReport:
        on_progress = kwargs.get("on_progress")
        if callable(on_progress):
            on_progress(1, 1)
        time.sleep(0.05)
        return dummy_report

    workflow_mock.run_suite.side_effect = fake_run_suite

    job = manager.submit_run(
        "test-agent",
        workflow_mock,
        endpoint_url="http://127.0.0.1:8000",
    )
    assert job.agent_id == "test-agent"
    assert job.status in (JobStatus.PENDING, JobStatus.RUNNING)

    # Poll until completed
    for _ in range(50):
        current = manager.get_job(job.run_id)
        assert current is not None
        if current.status == JobStatus.COMPLETED:
            break
        time.sleep(0.02)

    completed_job = manager.get_job(job.run_id)
    assert completed_job is not None
    assert completed_job.status == JobStatus.COMPLETED
    assert completed_job.progress.completed == 1
    assert completed_job.progress.total == 1
    assert completed_job.progress.percent == 100.0
    assert completed_job.completed_at is not None

    report = manager.get_report(job.run_id)
    assert report is dummy_report

    manager.shutdown(wait=True)


def test_run_job_manager_failure_lifecycle() -> None:
    manager = RunJobManager(max_concurrent_jobs=2)
    workflow_mock = MagicMock()
    workflow_mock.run_suite.side_effect = RuntimeError("Agent connection timed out")

    job = manager.submit_run(
        "test-agent",
        workflow_mock,
        endpoint_url="http://127.0.0.1:8000",
    )

    for _ in range(50):
        current = manager.get_job(job.run_id)
        assert current is not None
        if current.status == JobStatus.FAILED:
            break
        time.sleep(0.02)

    failed_job = manager.get_job(job.run_id)
    assert failed_job is not None
    assert failed_job.status == JobStatus.FAILED
    assert "Agent connection timed out" in (failed_job.error or "")
    assert failed_job.completed_at is not None

    manager.shutdown(wait=True)
