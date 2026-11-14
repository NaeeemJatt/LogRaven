"""SQLAlchemy ORM models for DSPM Data Assets and Classifications (PRD-MOD-08)."""

from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DSPMDataAsset(Base):
    __tablename__ = "dspm_data_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    storage_type: Mapped[str] = mapped_column(String(32), nullable=False)  # s3, blob, gcs, rds_postgres, bigquery
    total_objects_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sampled_objects_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contains_pii: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_pci: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_phi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_secrets: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    encryption_type: Mapped[str] = mapped_column(String(32), nullable=False, default="SSE_DEFAULT")  # NONE | SSE_DEFAULT | CMK_KMS
    is_ransomware_vulnerable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DSPMClassification(Base):
    __tablename__ = "dspm_classifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dspm_data_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # PII | PCI | PHI | SECRET
    detector_name: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="HIGH")  # HIGH | MEDIUM
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    byte_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
