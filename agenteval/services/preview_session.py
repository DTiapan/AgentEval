"""Short-lived preview sessions so freeze can persist without regenerating the pack."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from agenteval.db.migrations import apply_migrations
from agenteval.targets import TargetConnectionProfile


class PreviewSessionBinding(BaseModel):
    """Request parameters that must match when consuming a preview session."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    requirements_hash: str
    max_tests: int
    target_tier: str | None = None
    selected_test_ids: list[str] | None = None
    endpoint_url: str | None = None
    connection_profile_json: str | None = None


class PreviewSessionError(ValueError):
    """Invalid, expired, or mismatched preview session."""


def requirements_content_hash(requirements_text: str) -> str:
    return hashlib.sha256(requirements_text.encode("utf-8")).hexdigest()


def binding_from_request(
    *,
    agent_id: str,
    requirements_text: str,
    max_tests: int,
    target_tier: str | None,
    selected_test_ids: list[str] | None,
    endpoint_url: str | None,
    connection_profile: TargetConnectionProfile | None,
) -> PreviewSessionBinding:
    sorted_ids = sorted(selected_test_ids) if selected_test_ids else None
    profile_json = connection_profile.model_dump_json() if connection_profile else None
    return PreviewSessionBinding(
        agent_id=agent_id.strip(),
        requirements_hash=requirements_content_hash(requirements_text),
        max_tests=max_tests,
        target_tier=target_tier,
        selected_test_ids=sorted_ids,
        endpoint_url=(endpoint_url or "").strip() or None,
        connection_profile_json=profile_json,
    )


def _ttl_seconds() -> int:
    raw = os.getenv("AGENTEVAL_PREVIEW_SESSION_TTL_SECONDS", "7200").strip()
    try:
        return max(300, int(raw))
    except ValueError:
        return 7200


class PreviewSessionStore:
    """SQLite-backed preview payloads (same DB as suites)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        apply_migrations(self._conn)

    def close(self) -> None:
        self._conn.close()

    def save(self, binding: PreviewSessionBinding, preview_payload: dict) -> str:
        self._purge_expired()
        preview_id = uuid4().hex
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=_ttl_seconds())
        payload = dict(preview_payload)
        payload.pop("preview_id", None)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO preview_sessions (
                    id, created_at, expires_at, binding_json, payload_json, consumed_at
                ) VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (
                    preview_id,
                    now.isoformat(),
                    expires.isoformat(),
                    binding.model_dump_json(),
                    json.dumps(payload),
                ),
            )
        return preview_id

    def consume(self, preview_id: str, expected: PreviewSessionBinding) -> dict:
        self._purge_expired()
        row = self._conn.execute(
            "SELECT binding_json, payload_json, expires_at, consumed_at FROM preview_sessions WHERE id = ?",
            (preview_id.strip(),),
        ).fetchone()
        if row is None:
            raise PreviewSessionError(
                "Preview session not found or expired. Run Preview pack again, then freeze."
            )
        if row["consumed_at"]:
            raise PreviewSessionError(
                "Preview session already used. Run Preview pack again before freezing."
            )
        expires = datetime.fromisoformat(str(row["expires_at"]))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if datetime.now(UTC) > expires:
            raise PreviewSessionError("Preview session expired. Run Preview pack again, then freeze.")

        stored = PreviewSessionBinding.model_validate_json(str(row["binding_json"]))
        if stored != expected:
            raise PreviewSessionError(
                "Preview no longer matches current PRD, endpoint, or pack settings. Re-run Preview pack."
            )

        data = json.loads(str(row["payload_json"]))
        now = datetime.now(UTC).isoformat()
        with self._conn:
            self._conn.execute(
                "UPDATE preview_sessions SET consumed_at = ? WHERE id = ?",
                (now, preview_id.strip()),
            )
        return data

    def _purge_expired(self) -> None:
        now = datetime.now(UTC).isoformat()
        with self._conn:
            self._conn.execute("DELETE FROM preview_sessions WHERE expires_at < ?", (now,))
