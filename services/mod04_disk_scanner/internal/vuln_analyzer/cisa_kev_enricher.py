"""CISA Known Exploited Vulnerabilities (KEV) Catalog & Threat Intelligence Enricher."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

# Curated high-impact CISA KEV entries for local high-speed lookup
# In production, continuously synchronized with https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
DEFAULT_CISA_KEV_ENTRIES: Dict[str, Dict[str, Any]] = {
    "CVE-2021-44228": {
        "cve_id": "CVE-2021-44228",
        "vendor_project": "Apache",
        "product": "Log4j2",
        "vulnerability_name": "Apache Log4j2 JNDI Remote Code Execution Vulnerability (Log4Shell)",
        "date_added": "2021-12-10",
        "required_action": "Apply immediate mitigation or upgrade to log4j 2.15.0 or later.",
        "due_date": "2021-12-24",
        "known_ransomware_campaign_use": "Known",
    },
    "CVE-2022-0778": {
        "cve_id": "CVE-2022-0778",
        "vendor_project": "OpenSSL",
        "product": "OpenSSL",
        "vulnerability_name": "OpenSSL BN_mod_sqrt Infinite Loop Denial of Service Vulnerability",
        "date_added": "2022-03-25",
        "required_action": "Apply updates per vendor instructions.",
        "due_date": "2022-04-18",
        "known_ransomware_campaign_use": "Known",
    },
    "CVE-2023-38606": {
        "cve_id": "CVE-2023-38606",
        "vendor_project": "Apple",
        "product": "macOS and iOS",
        "vulnerability_name": "Apple Multiple Products Improper State Management Vulnerability",
        "date_added": "2023-07-25",
        "required_action": "Apply updates per vendor instructions.",
        "due_date": "2023-08-15",
        "known_ransomware_campaign_use": "Unknown",
    },
    "CVE-2024-21626": {
        "cve_id": "CVE-2024-21626",
        "vendor_project": "Open Containers Initiative",
        "product": "runc",
        "vulnerability_name": "runc Leaked File Descriptor Container Breakout Vulnerability",
        "date_added": "2024-02-05",
        "required_action": "Upgrade runc to version 1.1.12 or newer.",
        "due_date": "2024-02-26",
        "known_ransomware_campaign_use": "Known",
    },
    "CVE-2024-3094": {
        "cve_id": "CVE-2024-3094",
        "vendor_project": "Xun",
        "product": "XZ Utils",
        "vulnerability_name": "XZ Utils Malicious Code Injection Backdoor (Supply Chain Compromise)",
        "date_added": "2024-04-01",
        "required_action": "Revert to xz-utils 5.4 or trusted packaging.",
        "due_date": "2024-04-15",
        "known_ransomware_campaign_use": "Known",
    },
}


class CISAKEVEnricher:
    """Enriches CVE findings with CISA KEV active exploitation metadata."""

    def __init__(self, custom_entries: Optional[Dict[str, Dict[str, Any]]] = None):
        self._kev_map = dict(DEFAULT_CISA_KEV_ENTRIES)
        if custom_entries:
            self._kev_map.update(custom_entries)

    def is_known_exploited(self, cve_id: str) -> bool:
        """Returns True if the CVE is present on the CISA KEV list."""
        if not cve_id:
            return False
        return cve_id.strip().upper() in self._kev_map

    def get_kev_details(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full CISA KEV advisory record."""
        if not cve_id:
            return None
        return self._kev_map.get(cve_id.strip().upper())

    def register_kev(self, cve_id: str, details: Dict[str, Any]):
        """Dynamically registers or updates a KEV entry."""
        self._kev_map[cve_id.strip().upper()] = details

