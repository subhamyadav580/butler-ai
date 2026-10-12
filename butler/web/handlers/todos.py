from typing import Literal, Optional

from fastapi import Depends, HTTPException, Query, status

from butler.integrations.todos import TodoNotFound, TodoService
from butler.web.dependencies import get_todo_service
from butler.web.schemas.todos import (
    CreateTodoRequest,
    Todo,
    TodoListsResponse,
    TodosResponse,
    UpdateTodoRequest,
)


def _bad_request(error):
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(error))


def _not_found(error):
    return HTTPException(status.HTTP_404_NOT_FOUND, str(error))


async def list_todos(
    status_filter: Literal["open", "done", "all"] = Query("open", alias="status"),
    list: Optional[str] = None,
    query: Optional[str] = None,
    todos: TodoService = Depends(get_todo_service),
) -> TodosResponse:
    return TodosResponse(todos=todos.list(status_filter, list, query, limit=500))


async def list_todo_lists(todos: TodoService = Depends(get_todo_service)) -> TodoListsResponse:
    return TodoListsResponse(lists=todos.lists())


async def create_todo(
    request: CreateTodoRequest,
    todos: TodoService = Depends(get_todo_service),
) -> Todo:
    try:
        return Todo(**todos.add(request.title, request.due, request.list,
                                request.priority, request.notes))
    except ValueError as error:
        raise _bad_request(error)


async def update_todo(
    todo_id: int,
    request: UpdateTodoRequest,
    todos: TodoService = Depends(get_todo_service),
) -> Todo:
    try:
        return Todo(**todos.update(
            todo_id, title=request.title, due=request.due, clear_due=request.clear_due,
            list_name=request.list, priority=request.priority, notes=request.notes,
            done=request.done,
        ))
    except TodoNotFound as error:
        raise _not_found(error)
    except ValueError as error:
        raise _bad_request(error)


async def delete_todo(todo_id: int, todos: TodoService = Depends(get_todo_service)):
    try:
        todos.delete(todo_id)
    except TodoNotFound as error:
        raise _not_found(error)
    return {"ok": True}
