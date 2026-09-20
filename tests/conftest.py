"""Pytest configuration and shared fixtures for AgentEval."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_sandbox_dir() -> Generator[Path, None, None]:
    """Provides a clean temporary directory for sandbox testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
