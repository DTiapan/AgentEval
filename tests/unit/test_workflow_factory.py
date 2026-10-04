from pathlib import Path

import pytest

from agenteval.services.workflow_factory import (
    DEFAULT_SUITE_ROOT,
    create_suite_workflow,
    default_suite_root,
    persistence_status,
    resolve_suite_root,
)


def test_default_suite_root_standard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTEVAL_SUITE_ROOT", raising=False)
    monkeypatch.delenv("AGENTEVAL_DATA_DIR", raising=False)
    assert default_suite_root() == Path(".agenteval/suites")


def test_default_suite_root_with_data_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTEVAL_SUITE_ROOT", raising=False)
    monkeypatch.setenv("AGENTEVAL_DATA_DIR", "/app/data")
    assert default_suite_root() == Path("/app/data/suites")


def test_default_suite_root_with_explicit_suite_root_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTEVAL_DATA_DIR", "/app/data")
    monkeypatch.setenv("AGENTEVAL_SUITE_ROOT", "/custom/suites")
    assert default_suite_root() == Path("/custom/suites")


def test_resolve_suite_root_preserves_custom_path() -> None:
    custom = Path("/tmp/my-suites")
    assert resolve_suite_root(custom) == custom


def test_resolve_suite_root_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="path traversal"):
        resolve_suite_root("../../etc/passwd")

    with pytest.raises(ValueError, match="path traversal"):
        resolve_suite_root("foo/../bar")


def test_persistence_status_reports_suite_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTEVAL_DATA_DIR", "/app/data")
    status = persistence_status()
    assert status["suite_root"] == "/app/data/suites"


def test_create_suite_workflow_with_data_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTEVAL_DATA_DIR", "/app/data")
    monkeypatch.setenv("AGENTEVAL_USE_SQLITE", "1")
    wf = create_suite_workflow(DEFAULT_SUITE_ROOT)
    assert str(wf.suite_root) == "/app/data/suites"
