"""Audit log connector unit tests."""

from pathlib import Path

from agenteval.connectors.audit_log import AuditLogConnectorConfig, fetch_audit_evidence


def test_fetch_audit_evidence_reads_rows(tmp_path: Path) -> None:
    import sqlite3

    db = tmp_path / "audit.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE audit_log (id INTEGER PRIMARY KEY, action TEXT, ticket_id TEXT, detail TEXT)"
    )
    conn.execute(
        "INSERT INTO audit_log (action, ticket_id, detail) VALUES (?, ?, ?)",
        ("refund", "TCK-1", "ok"),
    )
    conn.commit()
    conn.close()

    payload = fetch_audit_evidence(
        AuditLogConnectorConfig(db_path=str(db), ticket_id="TCK-1"),
        expected_action="refund",
    )
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["action"] == "refund"
