"""SQLAlchemy ORM models for Module 02: Cross-Cloud Asset Discovery & CAASM."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import String, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import TypeDecorator, Text as SA_Text
import json

from app.models.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JSONCompatibleDict(TypeDecorator):
    """Fallback JSON representation that works across PostgreSQL and SQLite."""
    impl = SA_Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return "{}"
        if isinstance(value, dict):
            return json.dumps(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        try:
            return json.loads(value)
        except Exception:
            return {}


class CSPMAsset(Base):
    """Normalized multi-cloud asset entity with Canonical URN and SHA-256 state tracking."""
    __tablename__ = "cspm_assets"

    urn: Mapped[str] = mapped_column(String(512), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False) # aws, azure, gcp, oci, alibaba, k8s, saas
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    service: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(256), nullable=False)
    resource_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSONB().with_variant(JSONCompatibleDict, "sqlite"), default=dict)
    config_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_cspm_assets_tenant_provider", "tenant_id", "provider"),
        Index("idx_cspm_assets_tenant_service", "tenant_id", "service"),
    )

