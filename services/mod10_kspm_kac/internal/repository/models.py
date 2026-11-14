"""SQLAlchemy ORM models for Module 10: KSPM & Kubernetes Admission Controller (PRD-MOD-10)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class K8sCluster(Base):
    __tablename__ = "k8s_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    cluster_name: Mapped[str] = mapped_column(String(128), nullable=False)
    distribution: Mapped[str] = mapped_column(String(32), nullable=False, default="EKS")  # EKS | AKS | GKE | ON_PREM
    k8s_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.30.0")
    kac_webhook_installed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kac_enforcement_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="AUDIT")  # AUDIT | ENFORCE
    namespaces_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pods_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    admission_events: Mapped[List["K8sAdmissionEvent"]] = relationship(
        "K8sAdmissionEvent",
        back_populates="cluster",
        cascade="all, delete-orphan",
    )


class K8sAdmissionEvent(Base):
    __tablename__ = "k8s_admission_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("k8s_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    resource_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_name: Mapped[str] = mapped_column(String(128), nullable=False)
    namespace: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False, default="CREATE")
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    violated_policies: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    cluster: Mapped["K8sCluster"] = relationship("K8sCluster", back_populates="admission_events")
