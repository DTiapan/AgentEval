#!/usr/bin/env python3
"""NFR-B-07: fail if domain pack literals leak into backbone (outside allowlist)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKBONE = ROOT / "agenteval"
ALLOWLIST_DIRS = (
    BACKBONE / "packs",
    BACKBONE / "connectors",
    BACKBONE / "inspect_bridge",
)
FORBIDDEN_SNIPPETS = (
    "fintech.disclosure",
    "FIN-REFUND-DISCLOSURE",
    "refund_ceiling_usd",
    "agenteval_packs",
)


def is_allowlisted(path: Path) -> bool:
    for allowed in ALLOWLIST_DIRS:
        try:
            path.relative_to(allowed)
            return True
        except ValueError:
            continue
    return False


def main() -> int:
    violations: list[str] = []
    for path in BACKBONE.rglob("*.py"):
        if is_allowlisted(path):
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                violations.append(f"{path.relative_to(ROOT)}: contains '{snippet}'")
    if violations:
        print("Backbone domain string check failed:")
        for line in violations:
            print(f"  - {line}")
        return 1
    print("Backbone domain string check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
