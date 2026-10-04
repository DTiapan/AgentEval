"""Dual-Engine persistence (SQLite v1 + PostgreSQL v2 per ADR-007)."""

from agenteval.db.config import use_sqlite_persistence
from agenteval.db.connection import connect, init_schema
from agenteval.db.import_suites import import_suites_from_filesystem
from agenteval.db.postgres_repository import PostgresSuiteRepository
from agenteval.db.protocol import SuiteRepositoryProtocol
from agenteval.db.suite_repository import (
    SQLiteSuiteRepository,
    SuiteRepository,
    create_suite_repository,
)

__all__ = [
    "PostgresSuiteRepository",
    "SQLiteSuiteRepository",
    "SuiteRepository",
    "SuiteRepositoryProtocol",
    "connect",
    "create_suite_repository",
    "import_suites_from_filesystem",
    "init_schema",
    "use_sqlite_persistence",
]
