"""SQLAlchemy ORM models for Workload SBOMs and CVE Vulnerabilities (PRD-MOD-04)."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorkloadSBOM(Base):
    __tablename__ = "workload_sboms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    os_family: Mapped[str] = mapped_column(String(64), nullable=False)
    os_version: Mapped[str] = mapped_column(String(64), nullable=False)
    kernel_version: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    cyclonedx_sbom: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    packages_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scan_duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class WorkloadVulnerability(Base):
    __tablename__ = "workload_vulnerabilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    cve_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    package_name: Mapped[str] = mapped_column(String(128), nullable=False)
    installed_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fixed_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cvss_v3_score: Mapped[float] = mapped_column(Numeric(3, 1), nullable=False)
    is_cisa_kev: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    epss_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.0)
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    remediated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


Index("idx_workload_vulns_lookup", WorkloadVulnerability.asset_urn, WorkloadVulnerability.cve_id, WorkloadVulnerability.package_name, unique=True)

