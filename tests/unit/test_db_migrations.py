"""SQLite v002 additive migrations."""

from pathlib import Path

from agenteval.db.connection import connect, init_schema
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


def test_v002_migration_and_default_target_on_save_run(tmp_path: Path) -> None:
    db = tmp_path / "migrated.db"
    conn = connect(db)
    init_schema(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'targets'"
    ).fetchone()
    assert row is not None
    conn.close()

    repo = SuiteRepository(db)
    manifest = SuiteStore.new_manifest("mig-agent", "fp", "http://127.0.0.1:8765/chat")
    test = CandidateTest(
        id="t1",
        capability_id="req-abc",
        persona_id="p",
        name="n",
        user_prompt="hi",
        expected_behavior="ok",
    )
    pack = TestPack(
        agent_id="mig-agent",
        version=1,
        tests=[test],
        candidate_count=1,
        requirements_fingerprint="fp",
    )
    repo.init_suite(manifest, [test], pack)
    target_id = repo.ensure_default_target("mig-agent", "http://127.0.0.1:8765/chat")
    assert target_id is not None

    obs = ObservationBundle(
        test_id="t1",
        user_prompt="hi",
        response_text="ok",
        http_status=200,
        latency_ms=1.0,
    )
    report = SuiteRunReport(
        agent_id="mig-agent",
        run_id="run-mig",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=obs,
                rationale="ok",
                trajectory=build_blackbox_trajectory(obs, "PASS", "ok"),
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    repo.save_run("mig-agent", report, endpoint_url="http://127.0.0.1:8765/chat")
    run_row = repo._conn.execute(
        "SELECT target_id FROM assurance_runs WHERE run_id = ?",
        ("run-mig",),
    ).fetchone()
    repo.close()
    assert run_row is not None
    assert str(run_row["target_id"]) == target_id
