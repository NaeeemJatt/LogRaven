# LogRaven — API rate limiting (SlowAPI)

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def rate_limit_key(request: Request) -> str:
    if settings.TRUST_FORWARDED_FOR:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip() or get_remote_address(request)
    return get_remote_address(request)


limiter = Limiter(key_func=rate_limit_key)
