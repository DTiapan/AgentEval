"""Capture audit_log evidence during run persist when configured."""

import os
import sqlite3

from agenteval.connectors.audit_log import AuditLogConnectorConfig, audit_payload_json
from agenteval.packs.enabled import _run_audit_log_db_path, enabled_domain_pack_ids


def audit_log_db_path() -> str | None:
    override = _run_audit_log_db_path.get()
    if override:
        return override
    raw = os.environ.get("AGENTEVAL_AUDIT_LOG_DB_PATH", "").strip()
    return raw or None


def should_capture_audit_evidence(
    conn: sqlite3.Connection | None = None,
    suite_version_id: str | None = None,
) -> bool:
    if audit_log_db_path() is None:
        return False
    if enabled_domain_pack_ids():
        return True
    if conn is not None and suite_version_id:
        row = conn.execute(
            "SELECT 1 FROM suite_pack_selections WHERE suite_version_id = ? LIMIT 1",
            (suite_version_id,),
        ).fetchone()
        return row is not None
    return False


def build_audit_evidence_payload(test_data: dict[str, object]) -> str | None:
    db_path = audit_log_db_path()
    if db_path is None:
        return None
    ticket_id = test_data.get("ticket_id")
    expected = test_data.get("expected_audit_action")
    config = AuditLogConnectorConfig(
        db_path=db_path,
        ticket_id=str(ticket_id) if ticket_id is not None else None,
        action=str(expected) if expected is not None else None,
    )
    return audit_payload_json(
        config,
        expected_action=str(expected) if expected is not None else None,
    )
