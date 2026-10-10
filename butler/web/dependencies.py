"""FastAPI dependency providers."""

from fastapi import Header, HTTPException, Request, status

from butler.web.core.security import verify_token


def get_agent_service(request: Request):
    return request.app.state.agent_service


def get_chat_service(request: Request):
    return request.app.state.chat_service


def get_integration_service(request: Request):
    return request.app.state.integration_service


def require_auth(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    if not verify_token(token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required")
