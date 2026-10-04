"""SQLite SuiteRepository mirrors SuiteStore run persistence."""

from pathlib import Path

from agenteval.db.suite_repository import SuiteRepository
from agenteval.planning.execution_trace import build_blackbox_trajectory
from agenteval.planning.models import (
    CandidateTest,
    ObservationBundle,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.planning.suite_store import SuiteExistsError, SuiteStore


def _sample_pack(agent_id: str = "repo-agent") -> TestPack:
    test = CandidateTest(
        id="t1",
        capability_id="cap",
        persona_id="p1",
        name="Greet",
        user_prompt="hi",
        expected_behavior="greet",
    )
    return TestPack(
        agent_id=agent_id,
        version=1,
        tests=[test],
        candidate_count=1,
        requirements_fingerprint="fp",
    )


def test_init_suite_and_load_manifest(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    repo = SuiteRepository(db)
    manifest = SuiteStore.new_manifest("repo-agent", "fp1", "http://127.0.0.1/chat")
    pack = _sample_pack()
    pool = list(pack.tests)
    repo.init_suite(manifest, pool, pack)
    loaded = repo.load_manifest("repo-agent")
    assert loaded.agent_id == "repo-agent"
    assert loaded.requirements_fingerprint == "fp1"
    assert repo.load_pack("repo-agent").tests[0].id == "t1"


def test_init_suite_raises_without_force(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    repo = SuiteRepository(db)
    manifest = SuiteStore.new_manifest("repo-agent", "fp1", "")
    pack = _sample_pack()
    repo.init_suite(manifest, list(pack.tests), pack)
    try:
        repo.init_suite(manifest, list(pack.tests), pack, force=False)
    except SuiteExistsError:
        return
    raise AssertionError("expected SuiteExistsError")


def test_save_run_round_trips_trajectory(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    repo = SuiteRepository(db)
    manifest = SuiteStore.new_manifest("repo-agent", "fp1", "http://127.0.0.1/chat")
    pack = _sample_pack()
    repo.init_suite(manifest, list(pack.tests), pack)

    obs = ObservationBundle(
        test_id="t1",
        user_prompt="hi",
        response_text="hello",
        http_status=200,
        latency_ms=3.0,
    )
    trajectory = build_blackbox_trajectory(obs, "PASS", "ok")
    report = SuiteRunReport(
        agent_id="repo-agent",
        run_id="run-1",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=obs,
                rationale="ok",
                trajectory=trajectory,
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    repo.save_run("repo-agent", report, endpoint_url="http://127.0.0.1/chat")

    latest = repo.load_latest_run("repo-agent")
    assert latest is not None
    assert latest.run_id == "run-1"
    assert len(latest.results[0].trajectory) == len(trajectory)
    assert latest.results[0].trajectory[0].kind == "user_message"

    by_id = repo.load_run("repo-agent", "run-1")
    assert by_id is not None
    assert by_id.results[0].observation.response_text == "hello"


def test_delete_agent_cascades_and_removes_data(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    repo = SuiteRepository(db)
    manifest = SuiteStore.new_manifest("repo-agent", "fp1", "http://127.0.0.1/chat")
    pack = _sample_pack("repo-agent")
    repo.init_suite(manifest, list(pack.tests), pack)

    obs = ObservationBundle(
        test_id="t1",
        user_prompt="hi",
        response_text="hello",
        http_status=200,
        latency_ms=3.0,
    )
    trajectory = build_blackbox_trajectory(obs, "PASS", "ok")
    report = SuiteRunReport(
        agent_id="repo-agent",
        run_id="run-1",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=obs,
                rationale="ok",
                trajectory=trajectory,
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    repo.save_run("repo-agent", report, endpoint_url="http://127.0.0.1/chat")

    assert "repo-agent" in repo.list_agent_ids()
    assert repo.delete_agent("repo-agent") is True
    assert "repo-agent" not in repo.list_agent_ids()
    assert repo.load_latest_run("repo-agent") is None
    # Deleting non-existent agent returns False
    assert repo.delete_agent("repo-agent") is False
    assert repo.delete_agent("non-existent-agent") is False
    repo.close()


def test_save_and_get_run_job(tmp_path: Path) -> None:
    from agenteval.services.run_manager import JobStatus, RunJobInfo, RunProgress

    db = tmp_path / "test_jobs.db"
    repo = SuiteRepository(db)
    try:
        # None for non-existent run_id
        assert repo.get_run_job("missing-run") is None

        job = RunJobInfo(
            run_id="run-job-123",
            agent_id="test-agent",
            status=JobStatus.RUNNING,
            progress=RunProgress(completed=3, total=10, percent=30.0),
        )
        repo.save_run_job(job)

        fetched = repo.get_run_job("run-job-123")
        assert fetched is not None
        assert fetched.run_id == "run-job-123"
        assert fetched.agent_id == "test-agent"
        assert fetched.status == JobStatus.RUNNING
        assert fetched.progress.completed == 3
        assert fetched.progress.total == 10
        assert fetched.progress.percent == 30.0

        # Update to completed
        updated = job.model_copy(
            update={
                "status": JobStatus.COMPLETED,
                "progress": RunProgress(completed=10, total=10, percent=100.0),
            }
        )
        repo.save_run_job(updated)

        fetched2 = repo.get_run_job("run-job-123")
        assert fetched2 is not None
        assert fetched2.status == JobStatus.COMPLETED
        assert fetched2.progress.percent == 100.0
    finally:
        repo.close()
