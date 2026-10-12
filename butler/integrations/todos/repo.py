"""Data access for todos. No business rules (see service.py)."""

import time

TODO_SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    notes         TEXT,
    list          TEXT NOT NULL DEFAULT 'Inbox',
    priority      TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
    due           TEXT,              -- ISO date ("2026-10-14") or datetime with offset
    due_ts        REAL,              -- epoch seconds, for sorting and "overdue"
    done          INTEGER NOT NULL DEFAULT 0,
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL,
    completed_at  REAL
);

CREATE INDEX IF NOT EXISTS idx_todos_open ON todos(done, due_ts);
CREATE INDEX IF NOT EXISTS idx_todos_list ON todos(list);
"""

FIELDS = ("title", "notes", "list", "priority", "due", "due_ts", "done", "completed_at")


class TodoRepo:
    def __init__(self, db):
        self.db = db
        db.apply_schema(TODO_SCHEMA)

    def add(self, title, notes, list_name, priority, due, due_ts):
        now = time.time()
        cursor = self.db.execute(
            "INSERT INTO todos (title, notes, list, priority, due, due_ts, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, notes, list_name, priority, due, due_ts, now, now),
        )
        return self.get(cursor.lastrowid)

    def get(self, todo_id):
        return self.db.query_one("SELECT * FROM todos WHERE id = ?", (todo_id,))

    def find(self, done=None, list_name=None, query=None, due_before=None, limit=100):
        where, params = [], []
        if done is not None:
            where.append("done = ?")
            params.append(1 if done else 0)
        if list_name:
            where.append("list = ? COLLATE NOCASE")
            params.append(list_name)
        if query:
            where.append("(title LIKE ? OR notes LIKE ?)")
            params += [f"%{query}%", f"%{query}%"]
        if due_before is not None:
            where.append("due_ts IS NOT NULL AND due_ts <= ?")
            params.append(due_before)
        sql = "SELECT * FROM todos"
        if where:
            sql += " WHERE " + " AND ".join(where)
        # Open first; then by due date (no date last), priority, newest
        sql += (
            " ORDER BY done, due_ts IS NULL, due_ts,"
            " CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,"
            " created_at DESC LIMIT ?"
        )
        params.append(limit)
        return self.db.query(sql, params)

    def update(self, todo_id, **fields):
        fields = {k: v for k, v in fields.items() if k in FIELDS}
        if not fields:
            return self.get(todo_id)
        sets = ", ".join(f"{name} = ?" for name in fields) + ", updated_at = ?"
        self.db.execute(
            f"UPDATE todos SET {sets} WHERE id = ?",
            (*fields.values(), time.time(), todo_id),
        )
        return self.get(todo_id)

    def delete(self, todo_id):
        self.db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))

    def lists(self):
        return self.db.query(
            "SELECT list AS name, SUM(done = 0) AS open, SUM(done = 1) AS done "
            "FROM todos GROUP BY list COLLATE NOCASE ORDER BY list COLLATE NOCASE"
        )
