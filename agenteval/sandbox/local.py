"""Local filesystem and SQLite sandbox implementation with deterministic state hashing."""

import hashlib
import sqlite3
import time
from pathlib import Path

from agenteval.core.models import StateDiff, StateSnapshot
from agenteval.sandbox.base import Sandbox


class LocalSandbox(Sandbox):
    """Local ephemeral environment managing file and database mutations."""

    def __init__(self, root_dir: Path, sqlite_db: str | None = None) -> None:
        self.root_dir = Path(root_dir)
        self.sqlite_db_name = sqlite_db
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _hash_file(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file's contents."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return ""

    def _hash_sqlite_tables(self) -> dict[str, str]:
        """Compute content hashes for tables in the configured SQLite database."""
        if not self.sqlite_db_name:
            return {}

        db_path = self.root_dir / self.sqlite_db_name
        if not db_path.exists():
            return {}

        table_hashes: dict[str, str] = {}
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(f"SELECT * FROM {table} ORDER BY 1")  # noqa: S608
                rows = cursor.fetchall()
                row_str = str(rows).encode("utf-8")
                table_hashes[table] = hashlib.sha256(row_str).hexdigest()
            conn.close()
        except sqlite3.Error:
            pass

        return table_hashes

    def snapshot(self, snapshot_id: str) -> StateSnapshot:
        """Capture the current state of files and SQLite tables."""
        file_hashes: dict[str, str] = {}

        for p in self.root_dir.rglob("*"):
            if p.is_file():
                rel_path = str(p.relative_to(self.root_dir))
                # Skip the sqlite db itself from direct file hashing if handled as a DB
                if self.sqlite_db_name and rel_path == self.sqlite_db_name:
                    continue
                # Skip temp/lock/git files
                if any(part.startswith((".", "__")) for part in p.parts):
                    continue
                file_hashes[rel_path] = self._hash_file(p)

        db_hashes = self._hash_sqlite_tables()

        return StateSnapshot(
            snapshot_id=snapshot_id,
            timestamp_ns=time.time_ns(),
            file_hashes=file_hashes,
            db_hashes=db_hashes,
        )

    def diff(self, pre_snapshot: StateSnapshot, post_snapshot: StateSnapshot) -> StateDiff:
        """Compute Delta S between two snapshots."""
        pre_files = pre_snapshot.file_hashes
        post_files = post_snapshot.file_hashes

        files_added = sorted([f for f in post_files if f not in pre_files])
        files_deleted = sorted([f for f in pre_files if f not in post_files])
        files_modified = sorted(
            [f for f in post_files if f in pre_files and post_files[f] != pre_files[f]]
        )

        db_mutations: list[dict[str, str]] = []
        all_tables = set(pre_snapshot.db_hashes.keys()) | set(post_snapshot.db_hashes.keys())
        for table in sorted(all_tables):
            pre_hash = pre_snapshot.db_hashes.get(table)
            post_hash = post_snapshot.db_hashes.get(table)
            if pre_hash != post_hash:
                db_mutations.append(
                    {
                        "table": table,
                        "status": "MUTATED"
                        if (pre_hash and post_hash)
                        else ("ADDED" if post_hash else "DELETED"),
                        "pre_hash": pre_hash or "",
                        "post_hash": post_hash or "",
                    }
                )

        return StateDiff(
            pre_snapshot_id=pre_snapshot.snapshot_id,
            post_snapshot_id=post_snapshot.snapshot_id,
            files_added=files_added,
            files_modified=files_modified,
            files_deleted=files_deleted,
            db_mutations=db_mutations,
        )
