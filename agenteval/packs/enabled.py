"""Which domain packs are active for freeze (FR-P-05 precursor)."""

import os


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
