"""SQLite persistence configuration (ADR-004)."""

import os
from pathlib import Path

DEFAULT_WORKSPACE_ID = "local-dev"
DEFAULT_WORKSPACE_SLUG = "local-dev"
DEFAULT_WORKSPACE_NAME = "Local development"


def data_dir() -> Path:
    raw = os.environ.get("AGENTEVAL_DATA_DIR", ".agenteval")
    return Path(raw)


def get_database_url() -> str:
    """Return raw database connection URL from environment if configured."""
    return (os.environ.get("DATABASE_URL") or os.environ.get("AGENTEVAL_DATABASE_URL", "")).strip()


def is_postgres() -> bool:
    """Return True if DATABASE_URL points to a PostgreSQL instance."""
    url = get_database_url().lower()
    return url.startswith("postgres://") or url.startswith("postgresql://")


def database_backend() -> str:
    """Return active database backend identifier ('sqlite' or 'postgres')."""
    return "postgres" if is_postgres() else "sqlite"


def default_database_path() -> Path:
    return data_dir() / "agenteval.db"


def database_path() -> Path:
    url = get_database_url()
    if url.startswith("sqlite:///"):
        path_part = url.removeprefix("sqlite:///")
        return Path(path_part)
    return default_database_path()


def use_sqlite_persistence() -> bool:
    if is_postgres():
        return False
    flag = os.environ.get("AGENTEVAL_USE_SQLITE", "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return True
