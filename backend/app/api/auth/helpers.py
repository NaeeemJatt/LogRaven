# LogRaven — Auth Helper Functions
#
# PURPOSE:
#   Thin wrappers used by auth routes and dependencies.

from app.schemas.user import TokenResponse
from app.utils import security


def create_token_pair(user_id: str, tier: str) -> TokenResponse:
    """Generate access + refresh token pair for a user."""
    refresh_token, _ = security.create_refresh_token(user_id)
    return TokenResponse(
        access_token=security.create_access_token(user_id, tier),
        refresh_token=refresh_token,
    )


def verify_token_or_raise(token: str) -> dict:
    """Decode token, raise HTTP 401 on any failure."""
    return security.decode_token(token)
