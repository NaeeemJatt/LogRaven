"""Module 05: Lightweight eBPF Runtime Reachability Sensor & Container Drift Engine.

FastAPI Router and Sensor Event Ingestion Pipeline (PRD-MOD-05).
"""

from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from services.mod05_ebpf_sensor.internal.bpf_loader.ringbuf_consumer import ResourceGovernor
from services.mod05_ebpf_sensor.internal.drift_detector.overlayfs_checker import OverlayFSChecker
from services.mod05_ebpf_sensor.internal.mapper.proc_resolver import ProcessResolver
from services.mod05_ebpf_sensor.internal.repository.reachability_repo import ReachabilityRepository
from services.mod05_ebpf_sensor.internal.telemetry_exporter.reachability_publisher import ReachabilityPublisher

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Module 05: eBPF Sensor & Runtime Reachability"])

# Shared engine components
_resolver = ProcessResolver()
_drift_checker = OverlayFSChecker()
_governor = ResourceGovernor()
_publisher = ReachabilityPublisher()


# ── Request / Response Models ─────────────────────────────────────────────

class IngestExecEventRequest(BaseModel):
    asset_urn: str
    container_id: Optional[str] = None
    pid: int
    comm: str
    filename: str
    is_container_upper_layer: Optional[int] = 0


class IngestExecEventResponse(BaseModel):
    status: str
    resolved_package: Optional[str] = None
    resolved_version: Optional[str] = None
    is_container_drift: bool
    drift_alert: Optional[Dict[str, Any]] = None
    telemetry_emitted: Optional[Dict[str, Any]] = None


class DriftAlertItemResponse(BaseModel):
    id: str
    asset_urn: str
    container_id: str
    binary_path: str
    overlayfs_layer: str
    process_pid: int
    comm: str
    severity: str
    detected_at: datetime


# ── Pipeline Coordinator ──────────────────────────────────────────────────

async def process_execution_event(
    session: AsyncSession,
    event: Dict[str, Any],
    resolver: Optional[ProcessResolver] = None,
    drift_checker: Optional[OverlayFSChecker] = None,
    publisher: Optional[ReachabilityPublisher] = None,
) -> IngestExecEventResponse:
    """Processes an eBPF tracepoint event: resolves package, checks container drift, and persists."""
    res = resolver or _resolver
    checker = drift_checker or _drift_checker
    pub = publisher or _publisher

    asset_urn = event["asset_urn"]
    container_id = event.get("container_id")
    filename = event["filename"]
    pid = event.get("pid", 0)
    comm = event.get("comm", "")

    # 1. Check for container drift (execution from writable upperdir)
    drift_alert = checker.inspect_exec_event(event)
    is_drift = drift_alert is not None

    if is_drift:
        await ReachabilityRepository.record_drift_alert(
            session=session,
            asset_urn=asset_urn,
            container_id=container_id or "unknown",
            binary_path=filename,
            process_pid=pid,
            comm=comm,
            overlayfs_layer="upperdir",
            severity="CRITICAL",
        )

    # 2. Correlate file path to package name
    resolution = res.resolve(filename)
    pkg_name = resolution["package_name"] if resolution else os.path.basename(filename)
    pkg_ver = resolution["package_version"] if resolution else "unknown"

    # 3. Persist reachability signal
    await ReachabilityRepository.record_reachability(
        session=session,
        asset_urn=asset_urn,
        package_name=pkg_name,
        library_path=filename,
        container_id=container_id,
        is_container_drift=is_drift,
    )

    await session.commit()

    # 4. Emit telemetry
    telemetry = await pub.emit_reachability(
        asset_urn=asset_urn,
        package_name=pkg_name,
        library_path=filename,
        container_id=container_id,
        is_container_drift=is_drift,
    )

    return IngestExecEventResponse(
        status="PROCESSED",
        resolved_package=pkg_name,
        resolved_version=pkg_ver,
        is_container_drift=is_drift,
        drift_alert=drift_alert,
        telemetry_emitted=telemetry,
    )


# ── REST API Endpoints ───────────────────────────────────────────────────

@router.post("/telemetry", response_model=IngestExecEventResponse)
async def ingest_sensor_telemetry(
    req: IngestExecEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest eBPF execution event from node sensor daemon."""
    event_dict = req.model_dump()
    return await process_execution_event(session=db, event=event_dict)


@router.get("/reachability")
async def check_package_reachability(
    asset_urn: str = Query(...),
    package_name: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a vulnerable package is actively executing in memory on the workload."""
    is_reachable = await ReachabilityRepository.is_package_reachable(
        session=db,
        asset_urn=asset_urn,
        package_name=package_name,
    )
    return {
        "asset_urn": asset_urn,
        "package_name": package_name,
        "is_loaded_in_memory": is_reachable,
    }


@router.get("/drift-alerts", response_model=List[DriftAlertItemResponse])
async def list_container_drift_alerts(
    asset_urn: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List detected container drift execution alerts."""
    alerts = await ReachabilityRepository.list_drift_alerts(
        session=db,
        asset_urn=asset_urn,
        limit=limit,
        offset=offset,
    )
    return [
        DriftAlertItemResponse(
            id=str(a.id),
            asset_urn=a.asset_urn,
            container_id=a.container_id,
            binary_path=a.binary_path,
            overlayfs_layer=a.overlayfs_layer,
            process_pid=a.process_pid,
            comm=a.comm,
            severity=a.severity,
            detected_at=a.detected_at,
        )
        for a in alerts
    ]


@router.get("/health")
async def get_sensor_governor_health(
    current_user: User = Depends(get_current_user),
):
    """Check eBPF sensor resource governor metrics (CPU <= 1.5%, RAM <= 64 MB)."""
    return _governor.get_metrics()
