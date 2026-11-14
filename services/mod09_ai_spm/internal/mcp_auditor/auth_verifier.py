"""MCP Authentication & Transport Security Verifier (PRD-MOD-09).

Verifies whether MCP endpoints enforce mTLS, Bearer Token auth, or are unauthenticated.
"""

from typing import Any, Dict
from urllib.parse import urlparse
import ipaddress


class MCPAuthVerifier:
    """Evaluates exposure and authentication controls of an MCP endpoint."""

    @classmethod
    def evaluate_endpoint(
        cls,
        endpoint_url: str,
        auth_header_present: bool = False,
        requires_mtls: bool = False,
        network_binding: str = "0.0.0.0",
    ) -> Dict[str, Any]:
        """Evaluates whether an MCP endpoint is publicly exposed and if auth is enforced."""
        parsed = urlparse(endpoint_url if "://" in endpoint_url else f"http://{endpoint_url}")
        hostname = parsed.hostname or endpoint_url.split(":")[0]

        is_public = cls._is_public_host(hostname, network_binding)
        auth_enforced = auth_header_present or requires_mtls

        findings = []
        if is_public and not auth_enforced:
            findings.append({
                "finding_code": "CRITICAL_EXPOSED_MCP_SERVER",
                "severity": "CRITICAL",
                "description": f"MCP endpoint '{endpoint_url}' is exposed to public network without authentication.",
            })
        elif not auth_enforced:
            findings.append({
                "finding_code": "MEDIUM_UNAUTHENTICATED_MCP_SERVER",
                "severity": "MEDIUM",
                "description": f"MCP endpoint '{endpoint_url}' has no authentication enforced on private network.",
            })

        return {
            "endpoint_url": endpoint_url,
            "is_publicly_exposed": is_public,
            "auth_enforced": auth_enforced,
            "findings": findings,
        }

    @staticmethod
    def _is_public_host(host: str, binding: str) -> bool:
        """Determines if the endpoint is reachable from the public internet."""
        if host in ("localhost", "127.0.0.1", "::1") and binding not in ("0.0.0.0", "::"):
            return False

        if any(host.endswith(sfx) for sfx in (".local", ".internal", ".cluster.local", ".svc", ".corp")):
            return False

        # If bound to all interfaces (0.0.0.0), it is exposed to the network
        if binding in ("0.0.0.0", "::"):
            return True

        try:
            ip = ipaddress.ip_address(host)
            if ip.is_loopback:
                return False
            # Check standard RFC 1918 private ranges
            if (
                ip in ipaddress.ip_network("10.0.0.0/8")
                or ip in ipaddress.ip_network("172.16.0.0/12")
                or ip in ipaddress.ip_network("192.168.0.0/16")
            ):
                return False
            return True
        except ValueError:
            return True
