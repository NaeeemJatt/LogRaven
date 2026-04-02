# LogRaven — User Pydantic Schemas
#
# PURPOSE:
#   Defines the shapes of data coming IN (requests) and going OUT (responses).
#   Completely separate from SQLAlchemy models — never expose ORM objects directly.
#
# SCHEMAS:
#   UserCreate      — POST /auth/register request body
#   UserLogin       — POST /auth/login request body
#   UserResponse    — GET /user/me response (never includes password_hash)
#   TokenResponse   — response after register/login/refresh
#
# TODO Month 1 Week 1: Implement this file.

from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str  # min 8 chars — validate in service


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    tier: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None


class AuthSessionResponse(BaseModel):
    """HTTP shape after login/register/refresh; tokens omitted unless INCLUDE_TOKENS_IN_AUTH_JSON."""

    token_type: str = "bearer"
    access_token: str | None = None
    refresh_token: str | None = None
    user: UserResponse | None = None
