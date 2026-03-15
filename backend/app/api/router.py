# LogRaven — Master API Router
#
# PURPOSE:
#   Registers all sub-routers with their URL prefixes.
#   This file is imported by main.py once.
#   All route handlers live in their own sub-packages.
#
# TODO Month 1 Week 1: Import and register auth router.
# TODO Month 1 Week 3: Register investigations router.
# TODO Month 4 Week 1: Register reports router.

from fastapi import APIRouter

router = APIRouter()

# TODO: from app.api.auth.routes import router as auth_router
# TODO: router.include_router(auth_router, prefix="/auth", tags=["auth"])
# TODO: from app.api.investigations.routes import router as inv_router
# TODO: router.include_router(inv_router, prefix="/api/v1/investigations", tags=["investigations"])
# TODO: from app.api.reports.routes import router as rep_router
# TODO: router.include_router(rep_router, prefix="/api/v1/reports", tags=["reports"])
# TODO: from app.api.health.routes import router as health_router
# TODO: router.include_router(health_router, tags=["health"])
