"""Unit tests for LocalSandbox and StateDiff calculation."""

import sqlite3
from pathlib import Path

from agenteval.sandbox.local import LocalSandbox


def test_local_sandbox_lifecycle(temp_sandbox_dir: Path) -> None:
    """Test creating a sandbox and taking initial snapshot."""
    sandbox = LocalSandbox(root_dir=temp_sandbox_dir)
    snap1 = sandbox.snapshot("snap-pre")
    assert snap1.snapshot_id == "snap-pre"
    assert len(snap1.file_hashes) == 0

    # Create a file
    test_file = temp_sandbox_dir / "output.txt"
    test_file.write_text("Hello AgentEval")

    snap2 = sandbox.snapshot("snap-post")
    assert "output.txt" in snap2.file_hashes

    diff = sandbox.diff(snap1, snap2)
    assert diff.pre_snapshot_id == "snap-pre"
    assert diff.post_snapshot_id == "snap-post"
    assert "output.txt" in diff.files_added
    assert len(diff.files_deleted) == 0
    assert len(diff.files_modified) == 0


def test_local_sandbox_file_modifications(temp_sandbox_dir: Path) -> None:
    """Test file modification and deletion tracking."""
    file_a = temp_sandbox_dir / "a.txt"
    file_b = temp_sandbox_dir / "b.txt"
    file_a.write_text("v1")
    file_b.write_text("to delete")

    sandbox = LocalSandbox(root_dir=temp_sandbox_dir)
    snap1 = sandbox.snapshot("s1")

    # Modify file_a, delete file_b, add file_c
    file_a.write_text("v2")
    file_b.unlink()
    file_c = temp_sandbox_dir / "c.txt"
    file_c.write_text("new")

    snap2 = sandbox.snapshot("s2")
    diff = sandbox.diff(snap1, snap2)

    assert "c.txt" in diff.files_added
    assert "a.txt" in diff.files_modified
    assert "b.txt" in diff.files_deleted


def test_local_sandbox_sqlite_state(temp_sandbox_dir: Path) -> None:
    """Test SQLite database row tracking."""
    db_path = temp_sandbox_dir / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, item TEXT, amount REAL)")
    conn.commit()

    sandbox = LocalSandbox(root_dir=temp_sandbox_dir, sqlite_db="test.db")
    snap1 = sandbox.snapshot("snap-db-1")
    assert "orders" in snap1.db_hashes

    # Insert a record
    conn.execute("INSERT INTO orders (id, item, amount) VALUES (1, 'Widget', 49.99)")
    conn.commit()
    conn.close()

    snap2 = sandbox.snapshot("snap-db-2")
    assert snap1.db_hashes["orders"] != snap2.db_hashes["orders"]

    diff = sandbox.diff(snap1, snap2)
    assert len(diff.db_mutations) == 1
    assert diff.db_mutations[0]["table"] == "orders"
    assert diff.db_mutations[0]["status"] == "MUTATED"
