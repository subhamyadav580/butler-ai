import json
import logging

from fastapi import Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from butler.web.dependencies import get_agent_service
from butler.web.schemas.chat import (
    ConfirmActionAnswer,
    HistoryResponse,
    PickEmailAnswer,
    ResumeRequest,
    SendMessageRequest,
)
from butler.web.services.agent_service import AgentService, InterruptMismatch

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
    agent: AgentService = Depends(get_agent_service),
):
    return _sse(agent.send_message(request.thread_id, request.message))


async def resume(
    request: ResumeRequest,
    agent: AgentService = Depends(get_agent_service),
):
    try:
        answer = ANSWER_SCHEMAS[request.type].model_validate(request.answer)
    except ValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, error.errors())

    events = agent.resume(request.thread_id, request.type, answer.model_dump())

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


async def get_history(
    thread_id: str,
    agent: AgentService = Depends(get_agent_service),
) -> HistoryResponse:
    return HistoryResponse(**agent.history(thread_id))


async def reset_thread(
    thread_id: str,
    agent: AgentService = Depends(get_agent_service),
):
    agent.reset(thread_id)
    return {"ok": True}
