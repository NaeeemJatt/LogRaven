# LogRaven — Master API Router

from fastapi import APIRouter

from app.api.auth.routes import router as auth_router
from app.api.health.routes import router as health_router
from app.api.investigations.routes import router as inv_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(inv_router, prefix="/api/v1/investigations", tags=["investigations"])

# TODO Month 4 Week 1: Register reports router
# from app.api.reports.routes import router as rep_router
# router.include_router(rep_router, prefix="/api/v1/reports", tags=["reports"])
