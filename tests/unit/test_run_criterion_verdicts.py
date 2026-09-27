"""Slice 2: runs persist evidence_items and criterion_verdicts."""

from pathlib import Path

from agenteval.db.suite_repository import SuiteRepository
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.execution_trace import build_blackbox_trajectory
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult
from agenteval.planning.suite_store import SuiteStore


def test_save_run_writes_criterion_verdicts_with_evidence_links(tmp_path: Path) -> None:
    db = tmp_path / "run-verdicts.db"
    prd = (
        "# Agent\n\n## Capabilities\n"
        "- Process customer refund requests within the $100 ceiling.\n"
    )
    card = RequirementsIngestor.from_text(prd, agent_id="verdict-agent")
    fp = RequirementsIngestor.fingerprint_text(prd)
    pool, pack, _ = SuiteBootstrap(max_tests=4).build(card, fp)
    manifest = SuiteStore.new_manifest("verdict-agent", fp, "http://127.0.0.1:8765/chat")

    repo = SuiteRepository(db)
    repo.init_suite(
        manifest,
        pool,
        pack,
        agent_card_json=card.model_dump_json(),
        requirements_text=prd,
    )

    test = pack.tests[0]
    obs = ObservationBundle(
        test_id=test.id,
        user_prompt=test.user_prompt,
        response_text="I cannot process that without verification.",
        http_status=200,
        latency_ms=5.0,
    )
    trajectory = build_blackbox_trajectory(obs, "PASS", "refusal")
    report = SuiteRunReport(
        agent_id="verdict-agent",
        run_id="run-cv-1",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id=test.id,
                verdict="PASS",
                observation=obs,
                rationale="refusal",
                trajectory=trajectory,
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    repo.save_run("verdict-agent", report, endpoint_url="http://127.0.0.1:8765/chat")

    assert repo.count_criterion_verdicts("run-cv-1") >= 1
    row = repo._conn.execute(
        """
        SELECT COUNT(*) AS n FROM criterion_verdict_evidence cve
        JOIN criterion_verdicts cv ON cv.id = cve.verdict_id
        JOIN case_executions ce ON ce.id = cv.case_execution_id
        WHERE ce.run_id = ? AND cv.verdict = 'PASS'
        """,
        ("run-cv-1",),
    ).fetchone()
    repo.close()
    assert row is not None and int(row["n"]) >= 1


def test_unverifiable_criterion_has_no_evidence_link(tmp_path: Path) -> None:
    db = tmp_path / "run-unv.db"
    prd = "# Agent\n\n## Capabilities\n- Do the thing safely.\n"
    card = RequirementsIngestor.from_text(prd, agent_id="unv-agent")
    fp = RequirementsIngestor.fingerprint_text(prd)
    pool, pack, _ = SuiteBootstrap(max_tests=4).build(card, fp)
    manifest = SuiteStore.new_manifest("unv-agent", fp, "http://127.0.0.1:8765/chat")
    repo = SuiteRepository(db)
    repo.init_suite(
        manifest,
        pool,
        pack,
        agent_card_json=card.model_dump_json(),
        requirements_text=prd,
    )
    test = pack.tests[0]
    obs = ObservationBundle(
        test_id=test.id,
        user_prompt=test.user_prompt,
        response_text="HTTP error: connection refused",
        http_status=0,
        latency_ms=1.0,
    )
    report = SuiteRunReport(
        agent_id="unv-agent",
        run_id="run-unv",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id=test.id,
                verdict="UNVERIFIABLE",
                observation=obs,
                rationale="not reachable",
                trajectory=[],
            )
        ],
        passed=0,
        failed=0,
        unverifiable=1,
    )
    repo.save_run("unv-agent", report, endpoint_url="http://127.0.0.1:8765/chat")
    row = repo._conn.execute(
        """
        SELECT COUNT(*) AS n FROM criterion_verdict_evidence cve
        JOIN criterion_verdicts cv ON cv.id = cve.verdict_id
        JOIN case_executions ce ON ce.id = cv.case_execution_id
        WHERE ce.run_id = ?
        """,
        ("run-unv",),
    ).fetchone()
    repo.close()
    assert row is not None and int(row["n"]) == 0
