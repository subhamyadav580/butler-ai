from fastapi import HTTPException, status

from butler.web.core.security import auth_required, check_password, issue_token
from butler.web.schemas.auth import AuthStatusResponse, LoginRequest, LoginResponse


async def auth_status() -> AuthStatusResponse:
    return AuthStatusResponse(auth_required=auth_required())


async def login(request: LoginRequest) -> LoginResponse:
    if not check_password(request.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password")
    return LoginResponse(token=issue_token())
