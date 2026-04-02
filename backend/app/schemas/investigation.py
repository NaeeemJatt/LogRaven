# LogRaven — Investigation Pydantic Schemas
#
# PURPOSE:
#   Request/response shapes for investigation and file upload endpoints.
#
# SCHEMAS:
#   InvestigationCreate         — POST /api/v1/investigations
#   InvestigationFileResponse   — file detail in investigation responses
#   InvestigationResponse       — GET /api/v1/investigations/{id}
#   InvestigationStatusResponse — GET /api/v1/investigations/{id}/status
#
# TODO Month 1 Week 3: Implement this file.

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Any, Optional, List


class InvestigationCreate(BaseModel):
    name: str  # 1-200 chars


class InvestigationAnalyzeRequest(BaseModel):
    cloud_ai_consent: bool = False


class InvestigationFileResponse(BaseModel):
    id: UUID
    filename: str
    source_type: str
    log_type: Optional[str]
    status: str
    event_count: Optional[int]
    parser_detection_confidence: Optional[float] = None
    parser_selection_detail: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class InvestigationResponse(BaseModel):
    id: UUID
    name: str
    status: str
    correlation_enabled: bool
    cloud_ai_enabled: bool = False
    files: List[InvestigationFileResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationStatusResponse(BaseModel):
    id: UUID
    status: str
    progress_stage: Optional[str]  # queued/parsing/rule_engine/correlation/ai_analysis/building_report/complete (last step if failed)
    error_message: Optional[str] = None
    files: List[InvestigationFileResponse] = []
