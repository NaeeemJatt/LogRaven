# LogRaven — FastAPI Dependency Injectors
#
# PURPOSE:
#   Reusable async functions injected into route handlers by FastAPI.
#
# KEY INJECTORS:
#   get_db()           — yields async SQLAlchemy session, always closes after request
#   get_storage()      — returns correct StorageBackend based on config
#   get_current_user() — validates JWT, returns authenticated User object
#   require_pro_tier() — calls get_current_user + checks tier is pro/team

from typing import AsyncGenerator
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.config import settings
from app.utils.cookies import ACCESS_COOKIE
from app.utils.security import decode_token
from app.utils.storage import StorageBackend, create_storage_backend

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
access_cookie_scheme = APIKeyCookie(name=ACCESS_COOKIE, auto_error=False)

# ── Database engine (created once at module import) ──────────────────────────

_async_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_async_url, echo=settings.DEBUG, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── get_db ────────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── get_storage ───────────────────────────────────────────────────────────────

def get_storage() -> StorageBackend:
    return create_storage_backend()


# ── get_current_user ──────────────────────────────────────────────────────────

async def get_current_user(
    bearer_token: str | None = Depends(oauth2_scheme),
    cookie_token: str | None = Depends(access_cookie_scheme),
    db: AsyncSession = Depends(get_db),
):
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = bearer_token or cookie_token
    if not token:
        raise credentials_exc

    payload = decode_token(token)
    user_id: str | None = payload.get("sub")
    token_type: str | None = payload.get("type")
    if user_id is None or token_type != "access":
        raise credentials_exc

    from app.models.user import User  # local import avoids circular dependency

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc
    return user


# ── Pro / team tier gate (shared by Depends + route logic) ───────────────────

PRO_TIER_DETAIL = "This feature requires a pro or team tier account."


def ensure_pro_or_team_tier(user, *, detail: str = PRO_TIER_DETAIL) -> None:
    if user.tier not in ("pro", "team"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def require_pro_tier(current_user=Depends(get_current_user)):
    ensure_pro_or_team_tier(current_user)
    return current_user
