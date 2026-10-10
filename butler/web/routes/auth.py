from fastapi import APIRouter

from butler.web.handlers import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

router.add_api_route("/status", auth.auth_status, methods=["GET"])
router.add_api_route("/login", auth.login, methods=["POST"])
