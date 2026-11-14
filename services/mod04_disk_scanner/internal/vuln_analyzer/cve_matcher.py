"""Vulnerability Matcher (OSV / NVD / CVE) with CISA KEV and EPSS Correlation."""

import re
from typing import Any, Dict, List, Optional

from services.mod04_disk_scanner.internal.vuln_analyzer.cisa_kev_enricher import CISAKEVEnricher
from services.mod04_disk_scanner.internal.vuln_analyzer.epss_calculator import EPSSCalculator

# Known CVE Database definitions for common high-risk packages
CURATED_CVE_DATABASE: List[Dict[str, Any]] = [
    {
        "cve_id": "CVE-2022-0778",
        "package_name": "openssl",
        "vulnerable_version_regex": r"^(1\.0\.2[a-u]|1\.1\.1[a-m]|3\.0\.[0-1]).*",
        "fixed_version": "1.1.1n",
        "cvss_v3_score": 9.8,
        "description": "The BN_mod_sqrt() function, which computes a modular square root, contains an infinite loop bug.",
    },
    {
        "cve_id": "CVE-2022-0778",
        "package_name": "libssl1.1",
        "vulnerable_version_regex": r"^1\.1\.1[a-m].*",
        "fixed_version": "1.1.1n-0ubuntu0.20.04.1",
        "cvss_v3_score": 9.8,
        "description": "OpenSSL BN_mod_sqrt infinite loop.",
    },
    {
        "cve_id": "CVE-2021-44228",
        "package_name": "log4j-core",
        "vulnerable_version_regex": r"^2\.(0|[1-9]|1[0-4])(\..*)?$",
        "fixed_version": "2.15.0",
        "cvss_v3_score": 10.0,
        "description": "Log4Shell JNDI injection remote code execution.",
    },
    {
        "cve_id": "CVE-2024-21626",
        "package_name": "runc",
        "vulnerable_version_regex": r"^(1\.0\..*|1\.1\.[0-9]|1\.1\.1[0-1]).*",
        "fixed_version": "1.1.12",
        "cvss_v3_score": 9.3,
        "description": "runc container escape via /proc/self/fd leak.",
    },
    {
        "cve_id": "CVE-2024-3094",
        "package_name": "xz-utils",
        "vulnerable_version_regex": r"^5\.6\.[0-1].*",
        "fixed_version": "5.4.6",
        "cvss_v3_score": 10.0,
        "description": "Malicious code discovered in upstream tarballs of xz-utils.",
    },
]


class CVEMatcher:
    """Matches SBOM package inventory against vulnerability feeds and enriches with threat intel."""

    def __init__(
        self,
        cisa_enricher: Optional[CISAKEVEnricher] = None,
        epss_calculator: Optional[EPSSCalculator] = None,
        cve_database: Optional[List[Dict[str, Any]]] = None,
    ):
        self.kev = cisa_enricher or CISAKEVEnricher()
        self.epss = epss_calculator or EPSSCalculator()
        self.db = cve_database or list(CURATED_CVE_DATABASE)

    def scan_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scans list of CycloneDX package components and returns enriched vulnerability findings."""
        findings: List[Dict[str, Any]] = []

        for comp in components:
            pkg_name = comp.get("name", "").lower().strip()
            version = comp.get("version", "").strip()

            for rule in self.db:
                rule_pkg = rule["package_name"].lower().strip()
                if pkg_name != rule_pkg:
                    continue

                # Check version match
                regex = rule.get("vulnerable_version_regex")
                is_vuln = False
                if regex:
                    if re.match(regex, version):
                        is_vuln = True
                else:
                    is_vuln = True

                if is_vuln:
                    cve_id = rule["cve_id"]
                    is_kev = self.kev.is_known_exploited(cve_id)
                    epss_val = self.epss.get_score(cve_id)

                    finding = {
                        "cve_id": cve_id,
                        "package_name": comp.get("name"),
                        "installed_version": version,
                        "fixed_version": rule.get("fixed_version"),
                        "cvss_v3_score": float(rule["cvss_v3_score"]),
                        "is_cisa_kev": is_kev,
                        "epss_score": epss_val,
                        "description": rule.get("description", ""),
                        "bom_ref": comp.get("bom-ref"),
                    }
                    findings.append(finding)

        return findings

