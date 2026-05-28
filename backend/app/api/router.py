# LogRaven — Master API Router

from fastapi import APIRouter

from app.api.auth.routes import router as auth_router
from app.api.compliance.routes import router as compliance_router
from app.api.downloads.routes import router as downloads_router
from app.api.health.routes import router as health_router
from app.api.investigations.routes import router as inv_router
from app.api.play_parser.routes import router as play_parser_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(compliance_router, prefix="/api/v1", tags=["compliance"])
router.include_router(downloads_router, prefix="/api/v1/downloads", tags=["downloads"])
router.include_router(inv_router, prefix="/api/v1/investigations", tags=["investigations"])
router.include_router(play_parser_router, prefix="/api/v1/play-parser", tags=["play-parser"])

from app.api.reports.routes import router as rep_router
router.include_router(rep_router, prefix="/api/v1/reports", tags=["reports"])
