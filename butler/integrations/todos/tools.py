from typing import Literal, Optional

from langchain_core.tools import tool
from langgraph.types import interrupt

from .service import get_todo_service

Priority = Literal["low", "normal", "high"]
Status = Literal["open", "done", "all"]


@tool
def add_todo(
    title: str,
    due: Optional[str] = None,
    list: Optional[str] = None,
    priority: Priority = "normal",
    notes: Optional[str] = None,
) -> dict:
    """Add a todo to the user's Butler todo list.

    Args:
        title: What to do, short ("Pay electricity bill").
        due: Optional due date "2026-10-14" or date+time "2026-10-14T18:00",
            in the user's time zone.
        list: Optional list name ("Work", "Groceries"). Defaults to "Inbox".
            Reuse existing list names (see todo_lists).
        priority: low, normal or high.
        notes: Optional extra details.
    """
    return get_todo_service().add(title, due, list, priority, notes)


@tool
def list_todos(
    status: Status = "open",
    list: Optional[str] = None,
    query: Optional[str] = None,
    due_by: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List the user's todos: open first, then by due date and priority.

    Args:
        status: "open" (default), "done", or "all".
        list: Only this list ("Work").
        query: Only todos whose title or notes contain this text.
        due_by: Only todos due on or before this date/time ("2026-10-14"),
            e.g. for "what's due today" or "this week".
        limit: Maximum todos to return (1-200).
    """
    return get_todo_service().list(status, list, query, due_by, min(limit, 200))


@tool
def complete_todo(todo_id: int, done: bool = True) -> dict:
    """Mark a todo as done (or done=False to reopen it). Use the id from list_todos."""
    return get_todo_service().complete(todo_id, done)


@tool
def update_todo(
    todo_id: int,
    title: Optional[str] = None,
    due: Optional[str] = None,
    clear_due: bool = False,
    list: Optional[str] = None,
    priority: Optional[Priority] = None,
    notes: Optional[str] = None,
) -> dict:
    """Change a todo. Only the given fields change.

    Args:
        todo_id: From list_todos.
        title, list, priority, notes: New values.
        due: New due date/time ("2026-10-15" or "2026-10-15T09:00").
        clear_due: True to remove the due date.
    """
    return get_todo_service().update(
        todo_id, title=title, due=due, clear_due=clear_due,
        list_name=list, priority=priority, notes=notes,
    )


@tool
def delete_todo(todo_id: int) -> dict:
    """Permanently delete a todo. Asks the user to approve first.

    Prefer complete_todo when the user finished it; delete only when they
    ask to remove it.
    """
    service = get_todo_service()
    todo = service.get(todo_id)          # read-only: safe to repeat on resume

    details = f"#{todo['id']} {todo['title']} (list: {todo['list']})"
    if todo["due_human"]:
        details += f"\nDue: {todo['due_human']}"
    answer = interrupt({
        "type": "confirm_action",
        "question": "Delete this todo?",
        "tool": "delete_todo",
        "args": {"todo_id": todo_id},
        "details": details,
    })
    if not (answer or {}).get("approved"):
        return {"status": "rejected", "message": "The user kept the todo. Nothing was deleted."}

    service.delete(todo_id)
    return {"status": "deleted", "todo": todo}


@tool
def todo_lists() -> list[dict]:
    """The user's todo lists with counts of open and done todos."""
    return get_todo_service().lists()


TODO_TOOLS = [add_todo, list_todos, complete_todo, update_todo, delete_todo, todo_lists]
