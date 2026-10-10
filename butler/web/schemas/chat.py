from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=8000)


class PickEmailAnswer(BaseModel):
    email_id: Optional[str] = None  # None = cancel


class ConfirmActionAnswer(BaseModel):
    approved: bool


class ResumeRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100)
    # Which question is being answered: must match the pending interrupt
    type: Literal["pick_email", "confirm_action"]
    answer: dict[str, Any]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: Optional[float] = None


class Thread(BaseModel):
    id: str
    title: str
    created_at: float
    updated_at: float


class ThreadsResponse(BaseModel):
    threads: list[Thread]


class RenameThreadRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class HistoryResponse(BaseModel):
    messages: list[ChatMessage]
    pending: Optional[dict[str, Any]] = None
