# LogRaven — Asset Inventory Pydantic Schemas
#
# PURPOSE:
#   Request and response schemas for Cloud Asset Inventory API endpoints.

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class FilterItem(BaseModel):
    value: str
    count: int
    label: Optional[str] = None


class AssetResponse(BaseModel):
    urn: str
    account_id: str
    provider: str
    service: str
    resource_type: str
    resource_id: str
    resource_name: str
    region: str
    compliance_status: str
    failing_rule_count: int = 0
    passing_rule_count: int = 0
    tags: Dict[str, Any] = Field(default_factory=dict)
    first_seen_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetDetailResponse(AssetResponse):
    config_json: Dict[str, Any] = Field(default_factory=dict)
    config_sha256: str
    cloud_account_id: Optional[uuid.UUID] = None


class AssetListResponse(BaseModel):
    items: List[AssetResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class AssetFiltersResponse(BaseModel):
    providers: List[FilterItem]
    services: List[FilterItem]
    regions: List[FilterItem]
    statuses: List[FilterItem]


class AssetSummaryResponse(BaseModel):
    total_assets: int
    compliant_assets: int
    non_compliant_assets: int
    unassessed_assets: int
    services_count: int
    accounts_count: int


class AssetSyncRequest(BaseModel):
    cloud_account_id: Optional[uuid.UUID] = None


class AssetSyncResponse(BaseModel):
    status: str
    synced_assets_count: int
    services: List[str]
    message: str
    synced_at: str
