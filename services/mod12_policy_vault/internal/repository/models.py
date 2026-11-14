"""SQLAlchemy ORM models for Module 12: Visual-to-Rego Studio & Audit Vault (PRD-MOD-12)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CustomRegoRule(Base):
    __tablename__ = "custom_rego_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="HIGH")
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    visual_ast: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rego_code: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CrowdstrikeSuppressionRule(Base):
    __tablename__ = "crowdstrike_suppression_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    finding_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    account_ids: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    regions: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    tag_filters: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    approver: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)  # ACTIVE | EXPIRED | REVOKED
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class VaultPackage(Base):
    __tablename__ = "vault_packages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    package_name: Mapped[str] = mapped_column(String(128), nullable=False)
    merkle_root_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_hashes: Mapped[Dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    package_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

