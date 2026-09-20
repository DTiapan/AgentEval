"""Embedded persistence (SQLite v1)."""

from agenteval.db.config import use_sqlite_persistence
from agenteval.db.connection import connect, init_schema
from agenteval.db.import_suites import import_suites_from_filesystem
from agenteval.db.suite_repository import SuiteRepository

__all__ = [
    "SuiteRepository",
    "connect",
    "import_suites_from_filesystem",
    "init_schema",
    "use_sqlite_persistence",
]
