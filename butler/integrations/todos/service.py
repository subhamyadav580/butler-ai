"""Todo rules shared by the agent's tools and the web API.

Framework-agnostic: plain values in, plain dicts out.
"""

import time
from datetime import datetime, time as clock

from butler.config import local_tz
from butler.db import get_database
from butler.integrations.calendar.times import human, parse_when

from .repo import TodoRepo

PRIORITIES = ("low", "normal", "high")
DEFAULT_LIST = "Inbox"


class TodoNotFound(Exception):
    pass


class TodoService:
    def __init__(self, repo: TodoRepo):
        self.repo = repo

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def add(self, title, due=None, list_name=None, priority="normal", notes=None):
        title = (title or "").strip()
        if not title:
            raise ValueError("A todo needs a title.")
        due_iso, due_ts = _parse_due(due)
        row = self.repo.add(
            title, (notes or "").strip() or None, self._list_name(list_name),
            _priority(priority), due_iso, due_ts,
        )
        return _present(row)

    def update(self, todo_id, *, title=None, due=None, clear_due=False,
               list_name=None, priority=None, notes=None, done=None):
        self._require(todo_id)
        fields = {}
        if title is not None:
            if not title.strip():
                raise ValueError("A todo needs a title.")
            fields["title"] = title.strip()
        if clear_due:
            fields["due"], fields["due_ts"] = None, None
        elif due is not None:
            fields["due"], fields["due_ts"] = _parse_due(due)
        if list_name is not None:
            fields["list"] = self._list_name(list_name)
        if priority is not None:
            fields["priority"] = _priority(priority)
        if notes is not None:
            fields["notes"] = notes.strip() or None
        if done is not None:
            fields["done"] = 1 if done else 0
            fields["completed_at"] = time.time() if done else None
        return _present(self.repo.update(todo_id, **fields))

    def complete(self, todo_id, done=True):
        return self.update(todo_id, done=done)

    def delete(self, todo_id):
        todo = self.get(todo_id)
        self.repo.delete(todo_id)
        return todo

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, todo_id):
        return _present(self._require(todo_id))

    def list(self, status="open", list_name=None, query=None, due_by=None, limit=100):
        done = {"open": False, "done": True, "all": None}.get(status, False)
        due_before = None
        if due_by:
            due_before = _parse_due(due_by)[1]
        rows = self.repo.find(done, list_name, query, due_before, max(1, min(limit, 500)))
        return [_present(row) for row in rows]

    def lists(self):
        return [
            {"name": row["name"], "open": row["open"] or 0, "done": row["done"] or 0}
            for row in self.repo.lists()
        ]

    # ------------------------------------------------------------------

    def _require(self, todo_id):
        row = self.repo.get(int(todo_id))
        if not row:
            raise TodoNotFound(f"There is no todo #{todo_id}.")
        return row

    def _list_name(self, name):
        """Reuse an existing list's spelling ("work" → "Work")."""
        name = (name or "").strip() or DEFAULT_LIST
        for existing in self.repo.lists():
            if existing["name"].lower() == name.lower():
                return existing["name"]
        return name


def _priority(value):
    value = (value or "normal").strip().lower()
    if value not in PRIORITIES:
        raise ValueError(f"Priority must be one of: {', '.join(PRIORITIES)}.")
    return value


def _parse_due(value):
    """'2026-10-14' or '2026-10-14T15:00' → (stored ISO text, epoch for sorting).

    A date without a time counts as due by the end of that day.
    """
    if not value:
        return None, None
    when = parse_when(value)
    if isinstance(when, datetime):
        return when.isoformat(), when.timestamp()
    end_of_day = datetime.combine(when, clock(23, 59), tzinfo=local_tz())
    return when.isoformat(), end_of_day.timestamp()


def _present(row):
    due = parse_when(row["due"]) if row["due"] else None
    return {
        "id": row["id"],
        "title": row["title"],
        "notes": row["notes"],
        "list": row["list"],
        "priority": row["priority"],
        "due": row["due"],
        "due_human": human(due).replace(" (all day)", "") if due else None,
        "overdue": bool(row["due_ts"] and not row["done"] and row["due_ts"] < time.time()),
        "done": bool(row["done"]),
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }


_service = None


def get_todo_service():
    """The process-wide TodoService over data/butler.db."""
    global _service
    if _service is None:
        _service = TodoService(TodoRepo(get_database()))
    return _service
