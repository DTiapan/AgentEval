"""Construct SuiteWorkflow with shared persistence settings (ADR-004)."""

from pathlib import Path

from agenteval.db.config import database_path, use_sqlite_persistence
from agenteval.services.suite_workflow import SuiteWorkflow

DEFAULT_SUITE_ROOT = Path(".agenteval/suites")


def create_suite_workflow(
    suite_root: Path | str = DEFAULT_SUITE_ROOT,
    max_tests: int = 10,
    *,
    use_sqlite: bool | None = None,
    db_path: Path | str | None = None,
) -> SuiteWorkflow:
    sqlite_on = use_sqlite if use_sqlite is not None else use_sqlite_persistence()
    resolved_db = Path(db_path) if db_path is not None else database_path()
    return SuiteWorkflow(
        suite_root=suite_root,
        max_tests=max_tests,
        use_sqlite=sqlite_on,
        db_path=resolved_db if sqlite_on else None,
    )


def persistence_status(suite_root: Path | str = DEFAULT_SUITE_ROOT) -> dict[str, str | bool | None]:
    sqlite_on = use_sqlite_persistence()
    db = database_path()
    return {
        "sqlite_enabled": sqlite_on,
        "database_path": str(db) if sqlite_on else None,
        "suite_root": str(suite_root),
    }
