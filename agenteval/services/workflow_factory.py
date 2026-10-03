"""Construct SuiteWorkflow with shared persistence settings (ADR-004)."""

import os
from pathlib import Path

from agenteval.db.config import database_path, use_sqlite_persistence
from agenteval.services.suite_workflow import SuiteWorkflow


def default_suite_root() -> Path:
    raw = os.environ.get("AGENTEVAL_SUITE_ROOT", "").strip()
    if raw:
        return Path(raw)
    raw_data = os.environ.get("AGENTEVAL_DATA_DIR", "").strip()
    if raw_data:
        return Path(raw_data) / "suites"
    return Path(".agenteval/suites")


DEFAULT_SUITE_ROOT = Path(".agenteval/suites")


def resolve_suite_root(suite_root: Path | str | None = None) -> Path:
    if suite_root is not None and Path(suite_root) != DEFAULT_SUITE_ROOT:
        return Path(suite_root)
    return default_suite_root()


def create_suite_workflow(
    suite_root: Path | str = DEFAULT_SUITE_ROOT,
    max_tests: int = 10,
    *,
    use_sqlite: bool | None = None,
    db_path: Path | str | None = None,
) -> SuiteWorkflow:
    sqlite_on = use_sqlite if use_sqlite is not None else use_sqlite_persistence()
    resolved_db = Path(db_path) if db_path is not None else database_path()
    resolved_suite_root = resolve_suite_root(suite_root)
    return SuiteWorkflow(
        suite_root=resolved_suite_root,
        max_tests=max_tests,
        use_sqlite=sqlite_on,
        db_path=resolved_db if sqlite_on else None,
    )


def persistence_status(suite_root: Path | str = DEFAULT_SUITE_ROOT) -> dict[str, str | bool | None]:
    sqlite_on = use_sqlite_persistence()
    db = database_path()
    resolved_suite_root = resolve_suite_root(suite_root)
    return {
        "sqlite_enabled": sqlite_on,
        "database_path": str(db) if sqlite_on else None,
        "suite_root": str(resolved_suite_root),
    }

