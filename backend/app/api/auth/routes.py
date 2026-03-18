# LogRaven — Auth Routes
#
# PURPOSE:
#   HTTP route handlers for authentication.
#   All business logic lives in services/auth_service.py.
#   These handlers only: validate input, call service, return response.

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from app.services import auth_service


class RefreshRequest(BaseModel):
    refresh_token: str

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await auth_service.register_user(
        email=body.email,
        password=body.password,
        db=db,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await auth_service.login_user(
        email=body.email,
        password=body.password,
        db=db,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await auth_service.refresh_token(token=body.refresh_token, db=db)


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)) -> UserResponse:
    return current_user
