"""Stable requirement identifiers (FR-B-02)."""

import hashlib


def normalize_requirement_text(description: str) -> str:
    """Collapse whitespace and case for stable hashing."""
    return " ".join(description.strip().lower().split())


def requirement_stable_id(description: str) -> str:
    """Stable ID from requirement statement text; survives heading renames."""
    normalized = normalize_requirement_text(description)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"req-{digest[:12]}"
