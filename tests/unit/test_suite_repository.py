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
