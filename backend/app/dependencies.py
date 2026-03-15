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
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.config import settings
from app.utils.security import decode_token
from app.utils.storage import LocalStorageBackend, S3StorageBackend, StorageBackend

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

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
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageBackend(bucket=settings.S3_BUCKET_NAME, region=settings.AWS_REGION)
    return LocalStorageBackend(base_path=settings.LOCAL_STORAGE_PATH)


# ── get_current_user ──────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exc
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exc

    from app.models.user import User  # local import avoids circular dependency

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc
    return user


# ── require_pro_tier ─────────────────────────────────────────────────────────

async def require_pro_tier(current_user=Depends(get_current_user)):
    if current_user.tier not in ("pro", "team"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a pro or team tier account.",
        )
    return current_user
