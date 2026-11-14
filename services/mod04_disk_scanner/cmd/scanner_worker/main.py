"""Module 04: Out-of-Band Workload Disk Snapshot Scanner & SBOM/CVE Engine.

FastAPI Router and Scanner Worker Pipeline (PRD-MOD-04).
"""

from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from services.mod04_disk_scanner.internal.fs_reader.vfs_walker import VirtualFileSystem
from services.mod04_disk_scanner.internal.repository.sbom_repo import WorkloadRepository
from services.mod04_disk_scanner.internal.sbom_extractor.app_runtimes import AppRuntimeExtractor
from services.mod04_disk_scanner.internal.sbom_extractor.os_packages import OSPackageExtractor
from services.mod04_disk_scanner.internal.secret_scanner.pattern_matcher import SecretScanner
from services.mod04_disk_scanner.internal.snapshot_mgr.aws_ebs_cloner import AWSEBSCloner
from services.mod04_disk_scanner.internal.snapshot_mgr.cleaner import SnapshotCleaner
from services.mod04_disk_scanner.internal.vuln_analyzer.cisa_kev_enricher import CISAKEVEnricher
from services.mod04_disk_scanner.internal.vuln_analyzer.cve_matcher import CVEMatcher
from services.mod04_disk_scanner.internal.vuln_analyzer.epss_calculator import EPSSCalculator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Module 04: Workload Disk Snapshot Scanner"])

# Shared service instances
_cleaner = SnapshotCleaner(ttl_seconds=300)
_ebs_cloner = AWSEBSCloner(cleaner=_cleaner)
_cisa_enricher = CISAKEVEnricher()
_epss_calculator = EPSSCalculator()
_cve_matcher = CVEMatcher(cisa_enricher=_cisa_enricher, epss_calculator=_epss_calculator)


# ── Request / Response Models ─────────────────────────────────────────────

class ScanWorkloadRequest(BaseModel):
    asset_urn: str
    volume_id: str
    account_id: str
    region: str = "us-east-1"
    os_family_hint: str = "ubuntu"
    os_version_hint: str = "22.04"


class ScanWorkloadResponse(BaseModel):
    asset_urn: str
    scan_status: str
    scan_duration_sec: int
    packages_count: int
    vulnerabilities_count: int
    cisa_kev_count: int
    secrets_count: int
    sbom: Dict[str, Any]
    vulnerabilities: List[Dict[str, Any]]
    secrets: List[Dict[str, Any]]


class VulnerabilityItemResponse(BaseModel):
    id: str
    asset_urn: str
    cve_id: str
    package_name: str
    installed_version: str
    fixed_version: Optional[str]
    cvss_v3_score: float
    is_cisa_kev: bool
    epss_score: float
    first_detected_at: datetime


# ── Scan Coordinator Execution ────────────────────────────────────────────

async def execute_workload_scan(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    asset_urn: str,
    volume_id: str,
    account_id: str,
    region: str = "us-east-1",
    os_family: str = "ubuntu",
    os_version: str = "22.04",
    vfs: Optional[VirtualFileSystem] = None,
    cloner: Optional[AWSEBSCloner] = None,
    matcher: Optional[CVEMatcher] = None,
) -> Dict[str, Any]:
    """Coordinates out-of-band disk snapshot cloning, SBOM extraction, CVE matching, and secret scanning."""
    start_time = time.perf_counter()
    ebs = cloner or _ebs_cloner
    cve_engine = matcher or _cve_matcher

    # 1. Acquire ephemeral snapshot session (guarantees deletion < 300s)
    async with ebs.snapshot_session(volume_id=volume_id, account_id=account_id, region=region) as snap:
        logger.info(f"Scanning ephemeral snapshot {snap['snapshot_id']} for {asset_urn}")

        # 2. Extract package components from VFS
        fs = vfs or VirtualFileSystem()
        all_components: List[Dict[str, Any]] = []

        manifests = fs.find_package_manifests()
        for mtype, mpath, mcontent in manifests:
            if mtype == "dpkg":
                all_components.extend(OSPackageExtractor.parse_dpkg_status(mcontent))
            elif mtype == "apk":
                all_components.extend(OSPackageExtractor.parse_apk_installed(mcontent))
            elif mtype == "npm":
                all_components.extend(AppRuntimeExtractor.parse_package_lock_json(mcontent))
            elif mtype == "pip":
                all_components.extend(AppRuntimeExtractor.parse_requirements_txt(mcontent))
            elif mtype == "cargo":
                all_components.extend(AppRuntimeExtractor.parse_cargo_lock(mcontent))

        # Build CycloneDX v1.5 SBOM
        cyclonedx_sbom = OSPackageExtractor.build_cyclonedx_sbom(
            asset_urn=asset_urn,
            os_family=os_family,
            os_version=os_version,
            components=all_components,
        )

        # 3. Match CVEs & Threat Intel (CISA KEV + EPSS)
        detected_cves = cve_engine.scan_components(all_components)

        # 4. Scan for secrets & keys with automatic redaction
        secret_findings: List[Dict[str, Any]] = []
        cred_files = fs.find_credential_files()
        for fpath, fcontent in cred_files:
            secret_findings.extend(SecretScanner.scan_content(file_path=fpath, content=fcontent))

        elapsed_sec = max(1, int(time.perf_counter() - start_time))

        # 5. Persist to PostgreSQL database
        await WorkloadRepository.save_sbom(
            session=session,
            asset_urn=asset_urn,
            tenant_id=tenant_id,
            os_family=os_family,
            os_version=os_version,
            cyclonedx_sbom=cyclonedx_sbom,
            packages_count=len(all_components),
            scan_duration_sec=elapsed_sec,
        )

        saved_vulns = await WorkloadRepository.record_vulnerabilities(
            session=session,
            tenant_id=tenant_id,
            asset_urn=asset_urn,
            vulnerabilities=detected_cves,
        )

        await session.commit()

        cisa_kev_count = sum(1 for v in detected_cves if v.get("is_cisa_kev"))

        return {
            "asset_urn": asset_urn,
            "scan_status": "COMPLETED",
            "scan_duration_sec": elapsed_sec,
            "packages_count": len(all_components),
            "vulnerabilities_count": len(detected_cves),
            "cisa_kev_count": cisa_kev_count,
            "secrets_count": len(secret_findings),
            "sbom": cyclonedx_sbom,
            "vulnerabilities": detected_cves,
            "secrets": secret_findings,
        }


# ── REST API Endpoints ───────────────────────────────────────────────────

@router.post("/scan", response_model=ScanWorkloadResponse)
async def trigger_workload_scan(
    req: ScanWorkloadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger out-of-band disk snapshot scan, generating SBOM and detecting CVEs & secrets."""
    result = await execute_workload_scan(
        session=db,
        tenant_id=current_user.id,
        asset_urn=req.asset_urn,
        volume_id=req.volume_id,
        account_id=req.account_id,
        region=req.region,
        os_family=req.os_family_hint,
        os_version=req.os_version_hint,
    )
    return ScanWorkloadResponse(**result)


@router.get("/sboms/{asset_urn:path}")
async def get_workload_sbom(
    asset_urn: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the CycloneDX v1.5 Software Bill of Materials (SBOM) for an asset."""
    record = await WorkloadRepository.get_sbom(session=db, asset_urn=asset_urn, tenant_id=current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="SBOM not found for specified asset")
    return record.cyclonedx_sbom


@router.get("/vulnerabilities", response_model=List[VulnerabilityItemResponse])
async def list_workload_vulnerabilities(
    asset_urn: Optional[str] = Query(None),
    only_cisa_kev: bool = Query(False),
    min_cvss: Optional[float] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List detected CVE vulnerabilities across workloads with CISA KEV and CVSS filtering."""
    vulns = await WorkloadRepository.list_vulnerabilities(
        session=db,
        tenant_id=current_user.id,
        asset_urn=asset_urn,
        only_cisa_kev=only_cisa_kev,
        min_cvss=min_cvss,
        limit=limit,
        offset=offset,
    )
    return [
        VulnerabilityItemResponse(
            id=str(v.id),
            asset_urn=v.asset_urn,
            cve_id=v.cve_id,
            package_name=v.package_name,
            installed_version=v.installed_version,
            fixed_version=v.fixed_version,
            cvss_v3_score=float(v.cvss_v3_score),
            is_cisa_kev=v.is_cisa_kev,
            epss_score=float(v.epss_score),
            first_detected_at=v.first_detected_at,
        )
        for v in vulns
    ]

