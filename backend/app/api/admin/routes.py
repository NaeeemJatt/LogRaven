# LogRaven — Admin Routes
#
# Minimal operator surface until billing exists: lets a configured admin
# change a user's tier (free/pro/team), which is what unlocks upload sizes,
# AI ceilings, correlation, and daily quotas.
#
# Access: the authenticated caller's email must be listed in ADMIN_EMAILS
# (comma-separated env var). If ADMIN_EMAILS is empty these endpoints are
# disabled for everyone — there is no default admin.

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

VALID_TIERS = ("free", "pro", "team")


def _admin_emails() -> set[str]:
    return {e.strip().lower() for e in settings.ADMIN_EMAILS.split(",") if e.strip()}


def require_admin(current_user=Depends(get_current_user)):
    """Allow only users whose email is listed in ADMIN_EMAILS."""
    if current_user.email.lower() not in _admin_emails():
        # 404 (not 403) so the endpoint's existence isn't advertised to non-admins.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return current_user


class TierChangeRequest(BaseModel):
    email: EmailStr
    tier: str


class TierChangeResponse(BaseModel):
    email: str
    tier: str


@router.post("/users/tier", response_model=TierChangeResponse)
async def set_user_tier(
    request: Request,
    body: TierChangeRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TierChangeResponse:
    """Set a user's plan tier. Audited with actor + target."""
    if body.tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"tier must be one of {VALID_TIERS}")

    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    previous = user.tier
    user.tier = body.tier
    db.add(AuditLog(
        user_id=admin.id,
        action="tier_change",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata_={
            "target_user_id": str(user.id),
            "target_email": user.email,
            "from": previous,
            "to": body.tier,
        },
    ))
    await db.commit()
    logger.info("Admin %s changed tier for %s: %s -> %s", admin.email, user.email, previous, body.tier)
    return TierChangeResponse(email=user.email, tier=user.tier)
