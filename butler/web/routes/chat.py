from fastapi import APIRouter, Depends

from butler.web.dependencies import require_auth
from butler.web.handlers import chat

router = APIRouter(prefix="/api/chat", tags=["chat"], dependencies=[Depends(require_auth)])

router.add_api_route("/messages", chat.send_message, methods=["POST"])
router.add_api_route("/resume", chat.resume, methods=["POST"])
router.add_api_route("/threads/{thread_id}", chat.get_history, methods=["GET"])
router.add_api_route("/threads/{thread_id}", chat.reset_thread, methods=["DELETE"])
