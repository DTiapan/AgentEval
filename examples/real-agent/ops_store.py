"""SQLite store the ops agent mutates — AgentEval can later hash this as ΔS."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB = Path(".agenteval/real-agent-ops.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    ticket_id TEXT,
    detail TEXT NOT NULL
);
"""


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def seed(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO tickets (id, customer_id, status, notes)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("TCK-100", "cust-alice", "open", "Printer offline"),
            ("TCK-200", "cust-bob", "open", "VPN timeout"),
            ("TCK-300", "cust-alice", "resolved", "Password reset done"),
        ],
    )
    conn.commit()


def ticket_row(conn: sqlite3.Connection, ticket_id: str) -> dict[str, str] | None:
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return dict(row) if row else None


def list_tickets(conn: sqlite3.Connection, customer_id: str | None = None) -> list[dict[str, str]]:
    if customer_id:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE customer_id = ? ORDER BY id",
            (customer_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def update_ticket_status(
    conn: sqlite3.Connection, ticket_id: str, status: str, actor: str
) -> dict[str, str] | None:
    cur = conn.execute(
        "UPDATE tickets SET status = ? WHERE id = ?",
        (status, ticket_id),
    )
    if cur.rowcount == 0:
        return None
    conn.execute(
        "INSERT INTO audit_log (action, ticket_id, detail) VALUES (?, ?, ?)",
        ("update_status", ticket_id, f"{actor} set status={status}"),
    )
    conn.commit()
    return ticket_row(conn, ticket_id)


def delete_ticket(conn: sqlite3.Connection, ticket_id: str, actor: str) -> bool:
    cur = conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    if cur.rowcount == 0:
        return False
    conn.execute(
        "INSERT INTO audit_log (action, ticket_id, detail) VALUES (?, ?, ?)",
        ("delete_ticket", ticket_id, f"{actor} deleted ticket"),
    )
    conn.commit()
    return True
