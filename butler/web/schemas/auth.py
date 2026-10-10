from pydantic import BaseModel


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


class AuthStatusResponse(BaseModel):
    auth_required: bool
