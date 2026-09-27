"""Inspect 5a sidecar persistence when extra is available."""

from pathlib import Path

from agenteval.db.suite_repository import SuiteRepository
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.execution_trace import build_blackbox_trajectory
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult
from agenteval.planning.suite_store import SuiteStore


def test_inspect_log_columns_updated_when_extra_available(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "agenteval.inspect_bridge.log_archive.inspect_extra_available",
        lambda: True,
    )
    db = tmp_path / "inspect.db"
    prd = "# Agent\n\n## Capabilities\n- Do thing.\n"
    card = RequirementsIngestor.from_text(prd, agent_id="inspect-agent")
    fp = RequirementsIngestor.fingerprint_text(prd)
    pool, pack, _ = SuiteBootstrap(max_tests=4).build(card, fp)
    manifest = SuiteStore.new_manifest("inspect-agent", fp, "http://127.0.0.1:8765/chat")
    repo = SuiteRepository(db)
    repo.init_suite(manifest, pool, pack, agent_card_json=card.model_dump_json())
    test = pack.tests[0]
    obs = ObservationBundle(
        test_id=test.id,
        user_prompt=test.user_prompt,
        response_text="ok",
        http_status=200,
        latency_ms=1.0,
    )
    report = SuiteRunReport(
        agent_id="inspect-agent",
        run_id="run-inspect-1",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id=test.id,
                verdict="PASS",
                rationale="ok",
                observation=obs,
                trajectory=build_blackbox_trajectory(obs, "PASS", "ok"),
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    repo.save_run("inspect-agent", report, endpoint_url="http://127.0.0.1:8765/chat")
    row = repo._conn.execute(
        "SELECT inspect_log_path, inspect_log_sha256 FROM assurance_runs WHERE run_id = ?",
        ("run-inspect-1",),
    ).fetchone()
    repo.close()
    assert row is not None
    assert row["inspect_log_path"]
    assert row["inspect_log_sha256"]
