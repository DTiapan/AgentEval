"""Feature flags for B2 legacy vs B2′ scenario-first generation."""

import os


def legacy_b2_enabled() -> bool:
    """Persona × capability × hypothesis cross-product with meta-persona prefix."""
    raw = os.getenv("AGENTEVAL_LEGACY_B2", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def scenario_first_enabled() -> bool:
    """Scenario-first compiler (default on unless legacy or explicit off)."""
    if legacy_b2_enabled():
        return False
    raw = os.getenv("AGENTEVAL_SCENARIO_FIRST", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")
