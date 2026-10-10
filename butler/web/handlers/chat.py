import json
import logging

from fastapi import Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from butler.web.dependencies import get_chat_service
from butler.web.schemas.chat import (
    ConfirmActionAnswer,
    HistoryResponse,
    PickEmailAnswer,
    RenameThreadRequest,
    ResumeRequest,
    SendMessageRequest,
    Thread,
    ThreadsResponse,
)
from butler.web.services.agent_service import InterruptMismatch
from butler.web.services.chat_service import ChatService, ThreadNotFound

log = logging.getLogger(__name__)

ANSWER_SCHEMAS = {
    "pick_email": PickEmailAnswer,
    "confirm_action": ConfirmActionAnswer,
}


def _sse(events):
    """Turn service events into a Server-Sent Events response."""

    async def body():
        try:
            async for event in events:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as error:  # noqa: BLE001 — reported to the client
            log.exception("Chat stream failed")
            yield f"data: {json.dumps({'type': 'error', 'message': str(error)})}\n\n"

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def send_message(
    request: SendMessageRequest,
    chats: ChatService = Depends(get_chat_service),
):
    return _sse(chats.send_message(request.thread_id, request.message))


async def resume(
    request: ResumeRequest,
    chats: ChatService = Depends(get_chat_service),
):
    try:
        answer = ANSWER_SCHEMAS[request.type].model_validate(request.answer)
    except ValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, error.errors())

    events = chats.resume(request.thread_id, request.type, answer.model_dump())

    # Surface "nothing to resume" as 409 before the stream starts
    try:
        first = await anext(events)
    except InterruptMismatch as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error))
    except StopAsyncIteration:
        first = None

    async def replay():
        if first is not None:
            yield first
        async for event in events:
            yield event

    return _sse(replay())


async def list_threads(chats: ChatService = Depends(get_chat_service)) -> ThreadsResponse:
    return ThreadsResponse(threads=chats.list_threads())


async def get_history(
    thread_id: str,
    chats: ChatService = Depends(get_chat_service),
) -> HistoryResponse:
    return HistoryResponse(**chats.history(thread_id))


async def rename_thread(
    thread_id: str,
    request: RenameThreadRequest,
    chats: ChatService = Depends(get_chat_service),
) -> Thread:
    try:
        return Thread(**chats.rename(thread_id, request.title))
    except ThreadNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")


async def delete_thread(
    thread_id: str,
    chats: ChatService = Depends(get_chat_service),
):
    chats.delete(thread_id)
    return {"ok": True}
