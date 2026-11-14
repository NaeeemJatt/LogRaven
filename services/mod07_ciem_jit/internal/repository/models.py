"""SQLAlchemy ORM models for CIEM Entitlements and ChatOps JIT Leases (PRD-MOD-07)."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CloudEntitlement(Base):
    __tablename__ = "cloud_entitlements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    principal_arn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(16), nullable=False, default="aws")
    granted_actions: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    used_actions_90d: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    unused_actions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_toxic_combinations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    toxic_vectors: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    last_evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CloudJITLease(Base):
    __tablename__ = "cloud_jit_leases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    requester_email: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_role_arn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="REQUESTED", index=True)  # REQUESTED | APPROVED | ACTIVE | EXPIRED | REJECTED
    session_token_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

