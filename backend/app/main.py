# LogRaven — FastAPI Application Entry Point

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.limiter import limiter
from app.utils.exceptions import LogRavenError
from app.utils.logger import get_logger

access_log = get_logger("lograven.access")
app_log    = get_logger("lograven.app")

# ── Configure root uvicorn loggers to use same format ────────────────────────
logging.getLogger("uvicorn.access").handlers.clear()
logging.getLogger("uvicorn.error").handlers.clear()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_log.info("=" * 60)
    app_log.info("LogRaven API starting up")
    app_log.info("  Storage : %s  (%s)", settings.STORAGE_BACKEND, settings.LOCAL_STORAGE_PATH)
    app_log.info("  Debug   : %s", settings.DEBUG)
    app_log.info("=" * 60)

    os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, "reports"), exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, "playground"), exist_ok=True)

    # In in-process pipeline mode, a restart kills any in-flight analysis task.
    # Reset those orphaned rows so they don't hang in 'processing' forever.
    if settings.USE_ASYNCIO_INVESTIGATION_PIPELINE:
        try:
            from app.tasks.process_investigation import recover_orphaned_investigations

            recovered = await recover_orphaned_investigations()
            if recovered:
                app_log.warning(
                    "  Recovered %d investigation(s) interrupted by a previous restart",
                    recovered,
                )
        except Exception as exc:  # pragma: no cover - best-effort startup cleanup
            app_log.warning("  Orphan investigation recovery skipped: %s", exc)

    play_paths = sorted(
        {getattr(r, "path", "") for r in app.routes if "play-parser" in getattr(r, "path", "")}
    )
    if play_paths:
        app_log.info("  PlayParser : %s", " ".join(play_paths))
    else:
        app_log.warning(
            "  PlayParser : no routes (this process is not the current LogRaven API build)"
        )

    yield
    app_log.info("LogRaven API shut down.")


app = FastAPI(
    title="LogRaven API",
    description="Watch your logs. Find the threat.",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Access log middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def access_logger(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000

    # Color-code by status in the terminal
    status = response.status_code
    if status < 300:
        status_str = f"\033[32m{status}\033[0m"   # green
    elif status < 400:
        status_str = f"\033[33m{status}\033[0m"   # yellow
    elif status < 500:
        status_str = f"\033[33m{status}\033[0m"   # yellow
    else:
        status_str = f"\033[31m{status}\033[0m"   # red

    method = request.method.ljust(6)
    path = request.url.path
    if request.url.query:
        # Never log signed download JWTs (credential leak into log aggregators)
        if path == "/api/v1/downloads/file":
            path = f"{path}?token=<redacted>"
        else:
            path = f"{path}?{request.url.query}"

    access_log.info(
        "%s  %-45s  %s  %.1fms",
        method, path, status_str, ms,
    )
    return response

# ── CORS ─────────────────────────────────────────────────────────────────────

# In DEBUG, allow any localhost / 127.0.0.1 port so Vite (5173), alternate hosts, and
# VITE_API_URL=http://127.0.0.1:8000 still work with credentials.
_cors_origins = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"]
# Append explicit production origins from config (comma-separated), so a
# deployed frontend on a real domain works without widening the dev defaults.
_cors_origins += [
    origin.strip()
    for origin in settings.CORS_ALLOWED_ORIGINS.split(",")
    if origin.strip()
]
_cors_regex = (
    r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
    if settings.DEBUG
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ───────────────────────────────────────────────────────

@app.exception_handler(LogRavenError)
async def lograven_error_handler(request: Request, exc: LogRavenError) -> JSONResponse:
    app_log.warning("LogRavenError [%s]: %s  (%s %s)", exc.code, exc.message, request.method, request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code, "detail": None},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    app_log.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "code": "INTERNAL_ERROR", "detail": "An internal error occurred. Check server logs."},
    )

# ── Routers ──────────────────────────────────────────────────────────────────

from app.api.router import router  # noqa: E402

app.include_router(router)


@app.get("/")
def api_root():
    """Avoid bare 404 on /; full API is under /auth, /api/v1/..., /health."""
    return {"service": "LogRaven API", "docs": "/docs", "health": "/health"}
