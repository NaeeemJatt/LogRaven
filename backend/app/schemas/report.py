# LogRaven — Report Pydantic Schemas

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any


class FindingSchema(BaseModel):
    id: Optional[UUID] = None
    severity: str
    title: str
    description: str
    mitre_technique_id: Optional[str] = None
    mitre_technique_name: Optional[str] = None
    mitre_tactic: Optional[str] = None
    iocs: List[str] = []
    remediation: Optional[str] = None
    finding_type: str   # correlated | single
    source_files: List[str] = []
    confidence: float = 0.8

    model_config = ConfigDict(from_attributes=True)


class ReportResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    summary: Optional[str] = None
    severity_counts: dict
    correlated_findings: List[Any] = []
    single_source_findings: List[Any] = []
    mitre_techniques: List[str] = []
    findings: List[FindingSchema] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DownloadResponse(BaseModel):
    download_url: str
    filename: Optional[str] = None
    expires_in: int = 86400   # 24 hours
