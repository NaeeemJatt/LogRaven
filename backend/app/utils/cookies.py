# LogRaven — httpOnly auth cookies (not readable by JS)

from fastapi import Request, Response

from app.config import settings

ACCESS_COOKIE = "lr_access"
REFRESH_COOKIE = "lr_refresh"


def _is_secure_cookie(request: Request | None = None) -> bool:
    if settings.COOKIE_SECURE is False:
        return False
    if request is not None:
        # Check scheme or X-Forwarded-Proto header from reverse proxy (e.g. Nginx).
        # In RFC 6265bis, browsers strictly reject and discard cookies with the "Secure"
        # attribute received over plain HTTP (such as http://<IP> or http://domain without TLS).
        # If the incoming request explicitly arrived over HTTP, do not set secure=True.
        proto = request.headers.get("x-forwarded-proto", request.url.scheme).lower()
        if proto == "http":
            return False
    return bool(settings.COOKIE_SECURE)


def set_access_cookie(response: Response, access_token: str, request: Request | None = None) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=_is_secure_cookie(request),
        path="/",
    )


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    request: Request | None = None,
) -> None:
    set_access_cookie(response, access_token, request=request)
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        samesite="lax",
        secure=_is_secure_cookie(request),
        path="/",
    )


def clear_auth_cookies(response: Response, request: Request | None = None) -> None:
    sec = _is_secure_cookie(request)
    response.delete_cookie(
        ACCESS_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=sec,
    )
    response.delete_cookie(
        REFRESH_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=sec,
    )
