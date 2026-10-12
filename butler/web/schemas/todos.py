from typing import Literal, Optional

from pydantic import BaseModel, Field

Priority = Literal["low", "normal", "high"]


class Todo(BaseModel):
    id: int
    title: str
    notes: Optional[str] = None
    list: str
    priority: Priority
    due: Optional[str] = None
    due_human: Optional[str] = None
    overdue: bool
    done: bool
    created_at: float
    completed_at: Optional[float] = None


class TodosResponse(BaseModel):
    todos: list[Todo]


class TodoList(BaseModel):
    name: str
    open: int
    done: int


class TodoListsResponse(BaseModel):
    lists: list[TodoList]


class CreateTodoRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    due: Optional[str] = None
    list: Optional[str] = Field(default=None, max_length=100)
    priority: Priority = "normal"
    notes: Optional[str] = Field(default=None, max_length=5000)


class UpdateTodoRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    due: Optional[str] = None
    clear_due: bool = False
    list: Optional[str] = Field(default=None, max_length=100)
    priority: Optional[Priority] = None
    notes: Optional[str] = Field(default=None, max_length=5000)
    done: Optional[bool] = None
