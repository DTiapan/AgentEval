"""SQLite persistence configuration (ADR-004)."""

import os
from pathlib import Path

DEFAULT_WORKSPACE_ID = "local-dev"
DEFAULT_WORKSPACE_SLUG = "local-dev"
DEFAULT_WORKSPACE_NAME = "Local development"


def data_dir() -> Path:
    raw = os.environ.get("AGENTEVAL_DATA_DIR", ".agenteval")
    return Path(raw)


def default_database_path() -> Path:
    return data_dir() / "agenteval.db"


def database_path() -> Path:
    url = os.environ.get("AGENTEVAL_DATABASE_URL", "").strip()
    if url.startswith("sqlite:///"):
        path_part = url.removeprefix("sqlite:///")
        return Path(path_part)
    return default_database_path()


def use_sqlite_persistence() -> bool:
    flag = os.environ.get("AGENTEVAL_USE_SQLITE", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    return bool(os.environ.get("AGENTEVAL_DATABASE_URL", "").strip())
