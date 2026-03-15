# LogRaven — Report Pydantic Schemas
#
# PURPOSE:
#   Response shapes for report endpoints.
#
# TODO Month 4 Week 1: Implement this file.

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any


class FindingSchema(BaseModel):
    severity: str
    title: str
    description: str
    mitre_technique_id: Optional[str]
    mitre_technique_name: Optional[str]
    mitre_tactic: Optional[str]
    iocs: List[str] = []
    remediation: Optional[str]
    finding_type: str  # correlated or single
    source_files: List[str] = []


class ReportResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    summary: Optional[str]
    severity_counts: dict
    correlated_findings: List[Any] = []
    single_source_findings: List[Any] = []
    mitre_techniques: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class DownloadResponse(BaseModel):
    download_url: str
    expires_in: int = 86400  # 24 hours
