"""Shared helpers for planning package."""

import re


def slugify(text: str) -> str:
    """Convert arbitrary string into a clean URL/file-safe slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return cleaned or "default"
