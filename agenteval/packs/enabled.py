"""Which domain packs are active for freeze (FR-P-05 precursor)."""

import os
from contextvars import ContextVar

_run_audit_log_db_path: ContextVar[str | None] = ContextVar("run_audit_log_db_path", default=None)


def set_run_audit_log_db_path(path: str | None) -> None:
    _run_audit_log_db_path.set(path.strip() if path and path.strip() else None)


def enabled_domain_pack_ids() -> list[str]:
    """
    Comma-separated pack ids from ``AGENTEVAL_ENABLED_DOMAIN_PACKS``.

    Empty by default so spec-only freezes stay unchanged; set ``fintech`` to merge
    pack mandatory requirements at freeze.
    """
    raw = os.environ.get("AGENTEVAL_ENABLED_DOMAIN_PACKS", "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def resolve_enabled_pack_ids(explicit: list[str] | None) -> list[str]:
    """API/request list wins; otherwise fall back to env (may be empty)."""
    if explicit is not None:
        return [p.strip() for p in explicit if p and p.strip()]
    return enabled_domain_pack_ids()
