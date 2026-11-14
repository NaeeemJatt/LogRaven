"""Persistence repository for Runtime Reachability & Container Drift (PRD-MOD-05)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod05_ebpf_sensor.internal.repository.models import ContainerDriftAlert, WorkloadRuntimeReachability


class ReachabilityRepository:
    """High-throughput persistence layer for eBPF reachability events and drift alerts."""

    @staticmethod
    async def record_reachability(
        session: AsyncSession,
        asset_urn: str,
        package_name: str,
        library_path: str,
        container_id: Optional[str] = None,
        is_container_drift: bool = False,
    ) -> WorkloadRuntimeReachability:
        """Upserts a runtime package reachability signal."""
        now = datetime.now(timezone.utc)
        query = select(WorkloadRuntimeReachability).where(
            WorkloadRuntimeReachability.asset_urn == asset_urn,
            WorkloadRuntimeReachability.package_name == package_name,
            WorkloadRuntimeReachability.library_path == library_path,
            WorkloadRuntimeReachability.container_id == container_id,
        )
        result = await session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            existing.execution_count += 1
            existing.last_executed_at = now
            existing.is_loaded_in_memory = True
            if is_container_drift:
                existing.is_container_drift = True
            await session.flush()
            return existing
        else:
            record = WorkloadRuntimeReachability(
                asset_urn=asset_urn,
                container_id=container_id,
                package_name=package_name,
                library_path=library_path,
                is_loaded_in_memory=True,
                is_container_drift=is_container_drift,
                first_executed_at=now,
                last_executed_at=now,
                execution_count=1,
            )
            session.add(record)
            await session.flush()
            return record

    @staticmethod
    async def record_drift_alert(
        session: AsyncSession,
        asset_urn: str,
        container_id: str,
        binary_path: str,
        process_pid: int,
        comm: str,
        overlayfs_layer: str = "upperdir",
        severity: str = "CRITICAL",
    ) -> ContainerDriftAlert:
        """Records a new container drift execution alert."""
        now = datetime.now(timezone.utc)
        alert = ContainerDriftAlert(
            asset_urn=asset_urn,
            container_id=container_id,
            binary_path=binary_path,
            overlayfs_layer=overlayfs_layer,
            process_pid=process_pid,
            comm=comm,
            severity=severity,
            detected_at=now,
        )
        session.add(alert)
        await session.flush()
        return alert

    @staticmethod
    async def is_package_reachable(
        session: AsyncSession,
        asset_urn: str,
        package_name: str,
    ) -> bool:
        """Checks if a given package has actively been executed or loaded in memory."""
        query = select(WorkloadRuntimeReachability).where(
            WorkloadRuntimeReachability.asset_urn == asset_urn,
            WorkloadRuntimeReachability.package_name == package_name,
            WorkloadRuntimeReachability.is_loaded_in_memory == True,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def list_drift_alerts(
        session: AsyncSession,
        asset_urn: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ContainerDriftAlert]:
        """Lists container drift detection alerts."""
        query = select(ContainerDriftAlert)
        if asset_urn:
            query = query.where(ContainerDriftAlert.asset_urn == asset_urn)
        query = query.order_by(desc(ContainerDriftAlert.detected_at)).limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())
