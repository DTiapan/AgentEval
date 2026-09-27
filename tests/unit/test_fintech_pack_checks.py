"""Fintech pack check + audit_log evidence on run persist."""

import json
import sqlite3
from pathlib import Path

from agenteval.db.suite_repository import SuiteRepository
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult
from agenteval.planning.suite_store import SuiteStore


def _seed_audit_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            ticket_id TEXT,
            detail TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT INTO audit_log (action, ticket_id, detail) VALUES (?, ?, ?)",
        ("refund", "TCK-100", "refund for ORD-12345"),
    )
    conn.commit()
    conn.close()


def test_audit_check_passes_with_matching_log(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTEVAL_ENABLED_DOMAIN_PACKS", "fintech")
    audit_db = tmp_path / "audit.db"
    _seed_audit_db(audit_db)
    monkeypatch.setenv("AGENTEVAL_AUDIT_LOG_DB_PATH", str(audit_db))

    db = tmp_path / "suite.db"
    prd = "# Agent\n\n## Capabilities\n- Process refunds.\n"
    card = RequirementsIngestor.from_text(prd, agent_id="audit-agent")
    fp = RequirementsIngestor.fingerprint_text(prd)
    pool, pack, _ = SuiteBootstrap(max_tests=4).build(card, fp)
    manifest = SuiteStore.new_manifest("audit-agent", fp, "http://127.0.0.1:8765/chat")

    repo = SuiteRepository(db)
    repo.init_suite(manifest, pool, pack, agent_card_json=card.model_dump_json())
    test_id = pack.tests[0].id

    obs = ObservationBundle(
        test_id=test_id,
        user_prompt=pack.tests[0].user_prompt,
        response_text="Refund confirmed.",
        http_status=200,
        latency_ms=8.0,
    )
    report = SuiteRunReport(
        agent_id="audit-agent",
        run_id="run-audit-01",
        suite_version=pack.version,
        results=[
            TestCaseResult(
                test_id=test_id,
                verdict="PASS",
                rationale="http observable pass",
                observation=obs,
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    repo.save_run("audit-agent", report, endpoint_url="http://127.0.0.1:8765/chat")

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    audit_ev = conn.execute(
        "SELECT COUNT(*) AS c FROM evidence_items WHERE kind = 'audit_log'"
    ).fetchone()
    assert audit_ev is not None and int(audit_ev["c"]) >= 1

    audit_crit = conn.execute(
        """
        SELECT cv.verdict
        FROM criterion_verdicts cv
        JOIN acceptance_criteria ac ON ac.id = cv.criterion_id
        WHERE ac.check_kind = 'fintech.audit.refund_logged'
        """
    ).fetchone()
    assert audit_crit is not None
    assert str(audit_crit["verdict"]) == "PASS"
    conn.close()
    repo.close()
