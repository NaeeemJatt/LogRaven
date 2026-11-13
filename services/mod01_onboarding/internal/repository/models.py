"""SQLAlchemy ORM models for Module 01: Multi-Cloud Onboarding & Trust Broker."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Text, DateTime, LargeBinary, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.types import TypeDecorator, Text as SA_Text
import json

from app.models.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JSONCompatibleList(TypeDecorator):
    """Fallback list representation that works across PostgreSQL and SQLite."""
    impl = SA_Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return "[]"
        if isinstance(value, list):
            return json.dumps([str(x) for x in value])
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except Exception:
            return []


class CloudAccountV2(Base):
    """Multi-cloud account entity with encrypted ExternalId and zero static credentials."""
    __tablename__ = "cloud_accounts_v2"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(16), nullable=False) # aws, azure, gcp, oci, alibaba, k8s, saas
    native_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    organization_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    role_arn_or_sp: Mapped[str] = mapped_column(Text, nullable=False)
    external_id_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    event_stream_arn: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING_VALIDATION") # PENDING_VALIDATION, CONNECTED, DEGRADED, ERROR
    missing_permissions: Mapped[list] = mapped_column(JSONB().with_variant(JSONCompatibleList, "sqlite"), default=list)
    cloud_group_ids: Mapped[list] = mapped_column(JSONB().with_variant(JSONCompatibleList, "sqlite"), default=list)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)

    __table_args__ = (
        Index("ix_cloud_accounts_v2_tenant_provider", "tenant_id", "provider"),
        Index("ix_cloud_accounts_v2_status", "status"),
    )


class CloudGroup(Base):
    """Dynamic cloud grouping with business impact and environment categorization."""
    __tablename__ = "cloud_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    business_impact: Mapped[str] = mapped_column(String(16), nullable=False) # critical, high, medium, low
    environment: Mapped[str] = mapped_column(String(16), nullable=False) # prod, staging, dev
    account_ids: Mapped[list] = mapped_column(JSONB().with_variant(JSONCompatibleList, "sqlite"), default=list)
    tag_filters: Mapped[dict] = mapped_column(JSONB().with_variant(JSONCompatibleList, "sqlite"), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)

    __table_args__ = (
        Index("ix_cloud_groups_tenant_id", "tenant_id"),
    )

