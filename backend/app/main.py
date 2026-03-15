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


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_license(
        license_key=settings.LICENSE_KEY,
        bypass_dev=settings.LICENSE_BYPASS_DEV,
    )
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, "reports"), exist_ok=True)
    os.makedirs(os.path.join(settings.LOCAL_STORAGE_PATH, "uploads"), exist_ok=True)
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

# ── Global exception handlers ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "code": "INTERNAL_ERROR", "detail": str(exc)},
    )

# ── Static file serving for local PDF/upload storage ─────────────────────────

if settings.STORAGE_BACKEND == "local":
    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    app.mount("/files", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="files")

# ── Routers ──────────────────────────────────────────────────────────────────

from app.api.router import router  # noqa: E402 — imported after app creation

app.include_router(router)
