"""Repository for Workload SBOMs and CVE Vulnerabilities (PRD-MOD-04)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod04_disk_scanner.internal.repository.models import WorkloadSBOM, WorkloadVulnerability


class WorkloadRepository:
    """High-throughput persistence layer for SBOMs and workload CVE detections."""

    @staticmethod
    async def save_sbom(
        session: AsyncSession,
        asset_urn: str,
        tenant_id: uuid.UUID,
        os_family: str,
        os_version: str,
        cyclonedx_sbom: Dict[str, Any],
        packages_count: int,
        scan_duration_sec: int,
        kernel_version: Optional[str] = None,
    ) -> WorkloadSBOM:
        """Upserts an SBOM record for the specified workload asset."""
        now = datetime.now(timezone.utc)
        query = select(WorkloadSBOM).where(
            WorkloadSBOM.tenant_id == tenant_id,
            WorkloadSBOM.asset_urn == asset_urn,
        )
        result = await session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            existing.os_family = os_family
            existing.os_version = os_version
            existing.kernel_version = kernel_version
            existing.cyclonedx_sbom = cyclonedx_sbom
            existing.packages_count = packages_count
            existing.scan_duration_sec = scan_duration_sec
            existing.scanned_at = now
            await session.flush()
            return existing
        else:
            new_sbom = WorkloadSBOM(
                asset_urn=asset_urn,
                tenant_id=tenant_id,
                os_family=os_family,
                os_version=os_version,
                kernel_version=kernel_version,
                cyclonedx_sbom=cyclonedx_sbom,
                packages_count=packages_count,
                scan_duration_sec=scan_duration_sec,
                scanned_at=now,
            )
            session.add(new_sbom)
            await session.flush()
            return new_sbom

    @staticmethod
    async def get_sbom(
        session: AsyncSession,
        asset_urn: str,
        tenant_id: uuid.UUID,
    ) -> Optional[WorkloadSBOM]:
        """Retrieves the latest SBOM for an asset."""
        query = select(WorkloadSBOM).where(
            WorkloadSBOM.tenant_id == tenant_id,
            WorkloadSBOM.asset_urn == asset_urn,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def record_vulnerabilities(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        asset_urn: str,
        vulnerabilities: List[Dict[str, Any]],
    ) -> List[WorkloadVulnerability]:
        """Bulk upserts detected workload CVE vulnerabilities."""
        now = datetime.now(timezone.utc)
        saved_records = []

        for v in vulnerabilities:
            cve_id = v["cve_id"].strip()
            pkg = v["package_name"].strip()

            query = select(WorkloadVulnerability).where(
                WorkloadVulnerability.tenant_id == tenant_id,
                WorkloadVulnerability.asset_urn == asset_urn,
                WorkloadVulnerability.cve_id == cve_id,
                WorkloadVulnerability.package_name == pkg,
            )
            result = await session.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                existing.installed_version = v["installed_version"]
                existing.fixed_version = v.get("fixed_version")
                existing.cvss_v3_score = float(v["cvss_v3_score"])
                existing.is_cisa_kev = bool(v.get("is_cisa_kev", False))
                existing.epss_score = float(v.get("epss_score", 0.0))
                existing.remediated_at = None
                saved_records.append(existing)
            else:
                new_vuln = WorkloadVulnerability(
                    asset_urn=asset_urn,
                    tenant_id=tenant_id,
                    cve_id=cve_id,
                    package_name=pkg,
                    installed_version=v["installed_version"],
                    fixed_version=v.get("fixed_version"),
                    cvss_v3_score=float(v["cvss_v3_score"]),
                    is_cisa_kev=bool(v.get("is_cisa_kev", False)),
                    epss_score=float(v.get("epss_score", 0.0)),
                    first_detected_at=now,
                )
                session.add(new_vuln)
                saved_records.append(new_vuln)

        await session.flush()
        return saved_records

    @staticmethod
    async def list_vulnerabilities(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        asset_urn: Optional[str] = None,
        only_cisa_kev: bool = False,
        min_cvss: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorkloadVulnerability]:
        """Queries detected vulnerabilities with filtering for CISA KEV and CVSS thresholds."""
        query = select(WorkloadVulnerability).where(WorkloadVulnerability.tenant_id == tenant_id)

        if asset_urn:
            query = query.where(WorkloadVulnerability.asset_urn == asset_urn)
        if only_cisa_kev:
            query = query.where(WorkloadVulnerability.is_cisa_kev == True)
        if min_cvss is not None:
            query = query.where(WorkloadVulnerability.cvss_v3_score >= min_cvss)

        query = query.order_by(desc(WorkloadVulnerability.cvss_v3_score), desc(WorkloadVulnerability.first_detected_at))
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        return list(result.scalars().all())

