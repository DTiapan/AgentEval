"""Smoke tests for agenteval package initialization."""

import agenteval


def test_package_version() -> None:
    """Verify package exposes expected version."""
    assert agenteval.__version__ == "0.1.0"
