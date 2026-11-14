"""Integration tests for SBOM Generation and CVE Vulnerability Correlation.

Covers:
- TC-MOD4-001: 120-package Debian status parsing into CycloneDX v1.5 components
- TC-MOD4-002: Mock EBS volume containing unpatched OpenSSL on CISA KEV list
"""

from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from services.mod02_asset_crawler.internal.normalizer.urn_builder import build_urn
from services.mod04_disk_scanner.cmd.scanner_worker.main import execute_workload_scan
from services.mod04_disk_scanner.internal.fs_reader.vfs_walker import VirtualFileSystem
from services.mod04_disk_scanner.internal.repository.models import WorkloadSBOM, WorkloadVulnerability
from services.mod04_disk_scanner.internal.sbom_extractor.os_packages import OSPackageExtractor


def generate_mock_dpkg_status(package_count: int = 120) -> str:
    """Generates a realistic multi-package /var/lib/dpkg/status content string."""
    blocks = []
    for i in range(package_count):
        blocks.append(
            f"Package: libpkg-{i:03d}\n"
            f"Status: install ok installed\n"
            f"Priority: optional\n"
            f"Section: libs\n"
            f"Installed-Size: 1024\n"
            f"Maintainer: Debian Core Team <packages@debian.org>\n"
            f"Architecture: amd64\n"
            f"Version: 2.{i // 10}.{i % 10}-1ubuntu2\n"
            f"Description: Core shared library package #{i}\n"
            f" Extended description line for package #{i}\n"
        )
    return "\n".join(blocks)


def test_tc_mod4_001_debian_status_cyclonedx_sbom_extraction():
    """TC-MOD4-001: Feed raw Debian status file containing 120 packages into os_packages.py.
    
    Pass Criteria: Extractor outputs 120 validated CycloneDX components with accurate names,
    architectures, and version strings.
    """
    raw_status = generate_mock_dpkg_status(120)
    components = OSPackageExtractor.parse_dpkg_status(raw_status)

    assert len(components) == 120, f"Expected 120 components, got {len(components)}"

    # Validate first component
    first = components[0]
    assert first["name"] == "libpkg-000"
    assert first["version"] == "2.0.0-1ubuntu2"
    assert "pkg:deb/debian/libpkg-000@2.0.0-1ubuntu2?arch=amd64" == first["bom-ref"]
    assert any(p["name"] == "architecture" and p["value"] == "amd64" for p in first["properties"])

    # Validate last component
    last = components[-1]
    assert last["name"] == "libpkg-119"
    assert last["version"] == "2.11.9-1ubuntu2"
    assert "pkg:deb/debian/libpkg-119@2.11.9-1ubuntu2?arch=amd64" == last["bom-ref"]

    # Build full CycloneDX v1.5 document
    sbom = OSPackageExtractor.build_cyclonedx_sbom(
        asset_urn="urn:lograven:aws:123456789012:us-east-1:ec2:aws_instance/i-001",
        os_family="debian",
        os_version="12.4",
        components=components,
    )

    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert len(sbom["components"]) == 120
    assert sbom["metadata"]["component"]["name"] == "debian"


class MockDBSession:
    """Mock async DB session storing SBOM and Vulnerability records in-memory."""

    def __init__(self):
        self.sboms: dict[str, WorkloadSBOM] = {}
        self.vulns: dict[str, WorkloadVulnerability] = {}

    def add(self, obj):
        if isinstance(obj, WorkloadSBOM):
            self.sboms[obj.asset_urn] = obj
        elif isinstance(obj, WorkloadVulnerability):
            key = f"{obj.asset_urn}:{obj.cve_id}:{obj.package_name}"
            self.vulns[key] = obj

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def execute(self, query):
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_res.scalars.return_value.all.return_value = list(self.vulns.values())
        return mock_res


@pytest.mark.asyncio
async def test_tc_mod4_002_unpatched_openssl_cisa_kev_correlation():
    """TC-MOD4-002: Mock EBS volume containing an unpatched OpenSSL with CVE on CISA KEV list.
    
    Pass Criteria: Worker creates workload_vulnerabilities row with is_cisa_kev = true,
    cvss_v3_score >= 9.0, and correct package version.
    """
    tenant_id = uuid.uuid4()
    account_id = "123456789012"
    asset_urn = build_urn("aws", account_id, "us-east-1", "ec2", "aws_instance", "i-vulnerable-host")
    session = MockDBSession()

    # VFS containing unpatched openssl 1.1.1k vulnerable to CVE-2022-0778 (CISA KEV)
    vfs = VirtualFileSystem()
    vfs_dpkg_content = (
        "Package: openssl\n"
        "Status: install ok installed\n"
        "Architecture: amd64\n"
        "Version: 1.1.1k-1ubuntu2.1\n"
        "Description: Secure Sockets Layer toolkit\n\n"
        "Package: nginx\n"
        "Status: install ok installed\n"
        "Architecture: amd64\n"
        "Version: 1.18.0-0ubuntu1.4\n"
        "Description: High performance web server\n"
    )
    vfs.add_file("/var/lib/dpkg/status", vfs_dpkg_content)

    summary = await execute_workload_scan(
        session=session,
        tenant_id=tenant_id,
        asset_urn=asset_urn,
        volume_id="vol-01a2b3c4d5e6f7g8",
        account_id=account_id,
        region="us-east-1",
        os_family="ubuntu",
        os_version="20.04",
        vfs=vfs,
    )

    assert summary["scan_status"] == "COMPLETED"
    assert summary["packages_count"] == 2
    assert summary["vulnerabilities_count"] >= 1
    assert summary["cisa_kev_count"] >= 1

    # Find the OpenSSL finding
    openssl_vulns = [v for v in summary["vulnerabilities"] if v["package_name"] == "openssl"]
    assert len(openssl_vulns) == 1
    target_cve = openssl_vulns[0]

    assert target_cve["cve_id"] == "CVE-2022-0778"
    assert target_cve["is_cisa_kev"] is True
    assert target_cve["cvss_v3_score"] >= 9.0
    assert target_cve["installed_version"] == "1.1.1k-1ubuntu2.1"
    assert target_cve["epss_score"] > 0.8

