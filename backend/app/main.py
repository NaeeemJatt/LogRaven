# LogRaven — FastAPI Application Entry Point
#
# CRITICAL: validate_license() is called FIRST in startup event.
#           If license is invalid, SystemExit is raised and app does not start.

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.license import validate_license
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

    validate_license(
        license_key=settings.LICENSE_KEY,
        bypass_dev=settings.LICENSE_BYPASS_DEV,
    )
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, "reports"), exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, "uploads"), exist_ok=True)

    if settings.STORAGE_BACKEND == "local":
        if not any(r.name == "files" for r in app.routes):
            app.mount(
                "/files",
                StaticFiles(directory=settings.LOCAL_STORAGE_PATH),
                name="files",
            )

    yield
    app_log.info("LogRaven API shut down.")


app = FastAPI(
    title="LogRaven API",
    description="Watch your logs. Find the threat.",
    version="1.0.0",
    lifespan=lifespan,
)

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
    path   = request.url.path
    if request.url.query:
        path += f"?{request.url.query}"

    access_log.info(
        "%s  %-45s  %s  %.1fms",
        method, path, status_str, ms,
    )
    return response

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
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
