"""Data access for chat threads and their visible messages. No business rules."""

import time

CHAT_SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id   TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    created_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id, id);
CREATE INDEX IF NOT EXISTS idx_threads_updated ON threads(updated_at DESC);
"""


class ThreadRepo:
    def __init__(self, db):
        self.db = db

    def list(self, limit=200):
        return self.db.query(
            "SELECT id, title, created_at, updated_at FROM threads "
            "ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )

    def get(self, thread_id):
        return self.db.query_one(
            "SELECT id, title, created_at, updated_at FROM threads WHERE id = ?",
            (thread_id,),
        )

    def create(self, thread_id, title):
        now = time.time()
        self.db.execute(
            "INSERT OR IGNORE INTO threads (id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (thread_id, title, now, now),
        )

    def touch(self, thread_id):
        self.db.execute(
            "UPDATE threads SET updated_at = ? WHERE id = ?", (time.time(), thread_id)
        )

    def rename(self, thread_id, title):
        self.db.execute("UPDATE threads SET title = ? WHERE id = ?", (title, thread_id))

    def delete(self, thread_id):
        # Messages go with it (ON DELETE CASCADE)
        self.db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))


class MessageRepo:
    def __init__(self, db):
        self.db = db

    def add(self, thread_id, role, content):
        self.db.execute(
            "INSERT INTO messages (thread_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (thread_id, role, content, time.time()),
        )

    def list(self, thread_id):
        return self.db.query(
            "SELECT role, content, created_at FROM messages "
            "WHERE thread_id = ? ORDER BY id",
            (thread_id,),
        )
