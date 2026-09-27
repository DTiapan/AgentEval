"""Read-only audit_log evidence connector (SQLite append-only table)."""

import json
import sqlite3
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class AuditLogConnectorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    db_path: str = Field(min_length=1)
    ticket_id: str | None = None
    action: str | None = None
    limit: int = Field(default=20, ge=1, le=500)


def fetch_audit_evidence(
    config: AuditLogConnectorConfig,
    *,
    expected_action: str | None = None,
) -> dict[str, object]:
    path = Path(config.db_path)
    if not path.is_file():
        return {"rows": [], "error": "audit_db_missing", "expected_action": expected_action}

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        query = "SELECT action, ticket_id, detail FROM audit_log"
        clauses: list[str] = []
        params: list[object] = []
        if config.ticket_id:
            clauses.append("ticket_id = ?")
            params.append(config.ticket_id)
        if config.action:
            clauses.append("action = ?")
            params.append(config.action)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(config.limit)
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return {
        "rows": [dict(row) for row in rows],
        "ticket_id": config.ticket_id,
        "expected_action": expected_action or config.action,
    }


def audit_payload_json(
    config: AuditLogConnectorConfig,
    *,
    expected_action: str | None = None,
) -> str:
    return json.dumps(fetch_audit_evidence(config, expected_action=expected_action))
