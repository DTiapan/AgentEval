"""Capture audit_log evidence during run persist when configured."""

import os

from agenteval.connectors.audit_log import AuditLogConnectorConfig, audit_payload_json
from agenteval.packs.enabled import enabled_domain_pack_ids


def audit_log_db_path() -> str | None:
    raw = os.environ.get("AGENTEVAL_AUDIT_LOG_DB_PATH", "").strip()
    return raw or None


def should_capture_audit_evidence() -> bool:
    return bool(enabled_domain_pack_ids()) and audit_log_db_path() is not None


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
