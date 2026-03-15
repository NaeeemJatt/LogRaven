# LogRaven — FastAPI Application Entry Point
#
# CRITICAL: validate_license() is called FIRST in startup event.
#           If license is invalid, SystemExit is raised and app does not start.

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.license import validate_license
from app.utils.exceptions import LogRavenError


@asynccontextmanager
async def lifespan(app: FastAPI):
    # License validated before anything else initializes
    validate_license(
        license_key=settings.LICENSE_KEY,
        bypass_dev=settings.LICENSE_BYPASS_DEV,
    )
    # Ensure local storage directories exist
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, "reports"), exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, "uploads"), exist_ok=True)

    # Mount static file serving for local development (must happen after dir exists)
    if settings.STORAGE_BACKEND == "local":
        if not any(r.name == "files" for r in app.routes):
            app.mount(
                "/files",
                StaticFiles(directory=settings.LOCAL_STORAGE_PATH),
                name="files",
            )

    yield


app = FastAPI(
    title="LogRaven API",
    description="Watch your logs. Find the threat.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ───────────────────────────────────────────────────────

@app.exception_handler(LogRavenError)
async def lograven_error_handler(request: Request, exc: LogRavenError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code, "detail": None},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "code": "INTERNAL_ERROR", "detail": str(exc)},
    )

# ── Routers ──────────────────────────────────────────────────────────────────

from app.api.router import router  # noqa: E402

app.include_router(router)
