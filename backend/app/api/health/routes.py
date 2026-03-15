# LogRaven — Health Check Route
#
# PURPOSE:
#   GET /health — no auth required
#   Checks: database connectivity, Redis connectivity, Claude API reachability
#   Returns: {"status": "ok", "db": "ok", "redis": "ok", "claude_api": "ok"}
#   Used by monitoring tools and the client to verify installation.
#
# TODO Month 1 Week 1: Implement basic health check.

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    # TODO: Add real checks for DB, Redis, and Claude API
    return {"status": "ok", "db": "pending", "redis": "pending", "claude_api": "pending"}
