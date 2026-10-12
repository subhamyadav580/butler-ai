from fastapi import APIRouter, Depends

from butler.web.dependencies import require_auth
from butler.web.handlers import todos

router = APIRouter(prefix="/api/todos", tags=["todos"], dependencies=[Depends(require_auth)])

router.add_api_route("", todos.list_todos, methods=["GET"])
router.add_api_route("", todos.create_todo, methods=["POST"])
router.add_api_route("/lists", todos.list_todo_lists, methods=["GET"])
router.add_api_route("/{todo_id}", todos.update_todo, methods=["PATCH"])
router.add_api_route("/{todo_id}", todos.delete_todo, methods=["DELETE"])
