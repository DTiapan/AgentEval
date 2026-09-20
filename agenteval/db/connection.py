"""Open SQLite and apply schema DDL."""

import sqlite3
from pathlib import Path

from agenteval.db.config import database_path


def schema_sql_path() -> Path:
    return Path(__file__).resolve().parent / "schema.sql"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    ddl = schema_sql_path().read_text(encoding="utf-8")
    conn.executescript(ddl)
    conn.commit()
