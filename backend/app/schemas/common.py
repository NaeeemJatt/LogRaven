# LogRaven — Common Pydantic Schemas
#
# PURPOSE:
#   Shared response shapes used across multiple endpoints.

from pydantic import BaseModel
from typing import Optional


class ErrorResponse(BaseModel):
    error: str
    code: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str
    claude_api: str
