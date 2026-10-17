# LogRaven — Master API Router

from fastapi import APIRouter

from app.api.admin.routes import router as admin_router
from app.api.auth.routes import router as auth_router
from app.api.compliance.routes import router as compliance_router
from app.api.compliance.accounts import router as accounts_router
from app.api.compliance.auditor import router as auditor_router
from app.api.compliance.graph import router as graph_router
from app.api.dashboard.routes import router as dashboard_router
from app.api.downloads.routes import router as downloads_router
from app.api.health.routes import router as health_router
from app.api.investigations.routes import findings_router, router as inv_router
from app.api.meta.routes import router as meta_router
from app.api.play_parser.routes import router as play_parser_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(compliance_router, prefix="/api/v1", tags=["compliance"])
router.include_router(accounts_router, prefix="/api/v1", tags=["compliance-accounts"])
router.include_router(auditor_router, prefix="/api/v1", tags=["compliance-auditor"])
router.include_router(graph_router, prefix="/api/v1", tags=["compliance-graph"])
router.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["dashboard"])
router.include_router(downloads_router, prefix="/api/v1/downloads", tags=["downloads"])
router.include_router(inv_router, prefix="/api/v1/investigations", tags=["investigations"])
router.include_router(findings_router, prefix="/api/v1/findings", tags=["findings"])
router.include_router(meta_router, prefix="/api/v1/meta", tags=["meta"])
router.include_router(play_parser_router, prefix="/api/v1/play-parser", tags=["play-parser"])

from app.api.reports.routes import router as rep_router
router.include_router(rep_router, prefix="/api/v1/reports", tags=["reports"])
