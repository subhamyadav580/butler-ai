"""Shared SQLite connection (data/butler.db) for everything Butler stores.

One connection per process, guarded by a lock: queries are tiny and local,
so this is simpler than a pool and safe across threads. WAL mode lets the
web server and the Telegram bot (separate processes) share the file.

Each feature owns its tables and creates them with `apply_schema()`
(CREATE TABLE IF NOT EXISTS), e.g. web chats and todos.
"""

import sqlite3
import threading
from pathlib import Path

from butler.config import DATABASE_PATH


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False, timeout=10)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")

    def apply_schema(self, sql):
        """Create a feature's tables/indexes if they don't exist yet."""
        with self._lock, self._conn:
            self._conn.executescript(sql)

    def execute(self, sql, params=()):
        """Run a write statement in its own transaction; returns the cursor."""
        with self._lock, self._conn:
            return self._conn.execute(sql, params)

    def query(self, sql, params=()):
        with self._lock:
            return [dict(row) for row in self._conn.execute(sql, params).fetchall()]

    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def close(self):
        with self._lock:
            self._conn.close()


_database = None
_database_lock = threading.Lock()


def get_database():
    """The process-wide Database for DATABASE_PATH."""
    global _database
    with _database_lock:
        if _database is None:
            _database = Database(DATABASE_PATH)
        return _database
