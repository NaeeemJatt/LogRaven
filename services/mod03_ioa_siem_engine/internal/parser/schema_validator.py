"""OCSF v1.2 Schema Validator for Cloud Activity Audit Events."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OCSFCloudActivityEvent(BaseModel):
    """Normalized OCSF v1.2 Cloud Activity record model."""
    tenant_id: str
    event_time: str
    provider: str
    account_id: str
    region: str
    event_name: str
    read_only: int = Field(ge=0, le=1)
    actor_user_arn: str
    actor_session_mfa: int = Field(ge=0, le=1, default=0)
    src_ip: str
    is_external_ip: int = Field(ge=0, le=1)
    geo_country: str = "US"
    target_resource_urn: str
    status_code: str = "Success"
    error_code: Optional[str] = None
    raw_event_json: str


def validate_ocsf_record(data: Dict[str, Any]) -> OCSFCloudActivityEvent:
    """Validates dictionary against OCSF Cloud Activity Schema."""
    return OCSFCloudActivityEvent(**data)

