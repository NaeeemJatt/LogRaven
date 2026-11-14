"""SQLAlchemy ORM models for Workload Runtime Reachability and Container Drift (PRD-MOD-05)."""

from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WorkloadRuntimeReachability(Base):
    __tablename__ = "workload_runtime_reachability"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    container_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    package_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    library_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_loaded_in_memory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_container_drift: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    execution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ContainerDriftAlert(Base):
    __tablename__ = "container_drift_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    container_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    binary_path: Mapped[str] = mapped_column(String(512), nullable=False)
    overlayfs_layer: Mapped[str] = mapped_column(String(64), nullable=False, default="upperdir")
    process_pid: Mapped[int] = mapped_column(Integer, nullable=False)
    comm: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="CRITICAL")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


Index("idx_reachability_unique_pkg", WorkloadRuntimeReachability.asset_urn, WorkloadRuntimeReachability.package_name, WorkloadRuntimeReachability.library_path, WorkloadRuntimeReachability.container_id, unique=True)
