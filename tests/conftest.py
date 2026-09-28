"""Pytest configuration and shared fixtures for AgentEval."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _set_test_offline_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure unit tests run deterministically offline without slow external API calls."""
    monkeypatch.setenv("AGENTEVAL_FORCE_LOCAL", "1")
    monkeypatch.setenv("AGENTEVAL_FORCE_OFFLINE", "1")


@pytest.fixture
def temp_sandbox_dir() -> Generator[Path, None, None]:
    """Provides a clean temporary directory for sandbox testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
