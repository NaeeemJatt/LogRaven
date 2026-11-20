"""
LogRaven — Deterministic CSPM & Non-AI Engine Models (Module 02).
ORM models for CSPM controls, policies, mandates, and evaluation findings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CSPMControlCatalog(Base):
    """Catalog of all 1,565 controls from Qualys TotalCloud across AWS, Azure, GCP, and OCI."""

    __tablename__ = "cspm_controls_catalog"

    cid: Mapped[str] = mapped_column(String(32), primary_key=True)
    control_name: Mapped[str] = mapped_column(Text, nullable=False)
    service: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    control_type: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_type: Mapped[str] = mapped_column(String(32), nullable=False)
    criticality: Mapped[str] = mapped_column(String(16), nullable=False)
    rule_spec_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    modified_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    findings: Mapped[List[CSPMEvaluationFinding]] = relationship(
        "CSPMEvaluationFinding",
        back_populates="control",
        cascade="all, delete-orphan",
    )


class CSPMPolicyCatalog(Base):
    """Catalog of 29 built-in security policies mapped to controls."""

    __tablename__ = "cspm_policies_catalog"

    policy_title: Mapped[str] = mapped_column(String(255), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    execution_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mapped_cids: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    modified_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CSPMMandateCatalog(Base):
    """Catalog of 38 compliance mandates (SOC 2, ISO 27001, PCI-DSS, etc.)."""

    __tablename__ = "cspm_mandates_catalog"

    mandate_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mapped_cids: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    last_modified_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CSPMEvaluationFinding(Base):
    """Individual control evaluation verdict and evidence record per resource."""

    __tablename__ = "cspm_evaluation_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cid: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("cspm_controls_catalog.cid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_urn: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    service: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)  # PASS | FAIL
    criticality: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    control: Mapped[CSPMControlCatalog] = relationship("CSPMControlCatalog", back_populates="findings")

    __table_args__ = (
        UniqueConstraint("tenant_id", "cid", "resource_urn", name="uq_cspm_findings_tenant_cid_urn"),
        CheckConstraint("status IN ('PASS', 'FAIL')", name="ck_cspm_findings_status"),
        Index("idx_findings_tenant_status", "tenant_id", "status", "criticality"),
    )
