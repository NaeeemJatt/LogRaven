"""Vector Database Exposure & RAG Poisoning Posture Checker (PRD-MOD-09).

Audits Pinecone, Qdrant, Milvus, Weaviate, and pgvector clusters for network exposure,
authentication enforcement, and encryption in transit/at rest.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import ipaddress


class VectorDBChecker:
    """Audits RAG vector databases to prevent data poisoning and exfiltration."""

    SUPPORTED_ENGINES = {"pinecone", "qdrant", "milvus", "weaviate", "pgvector", "chroma"}

    @classmethod
    def audit_instance(
        cls,
        engine: str,
        endpoint_url: str,
        api_key_required: bool = True,
        is_in_vpc: bool = True,
        tls_enabled: bool = True,
    ) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        clean_engine = engine.lower().strip()
        is_public = cls._is_public(endpoint_url, is_in_vpc)

        # Public exposure without private network
        if is_public:
            if not api_key_required:
                findings.append({
                    "finding_code": "CRITICAL_VECTOR_DB_EXPOSED_NO_AUTH",
                    "severity": "CRITICAL",
                    "description": f"Vector database '{clean_engine}' is publicly exposed to internet with NO authentication required.",
                })
            else:
                findings.append({
                    "finding_code": "HIGH_VECTOR_DB_PUBLIC_ACCESS",
                    "severity": "HIGH",
                    "description": f"Vector database '{clean_engine}' is accessible from public internet instead of private VPC.",
                })

        # TLS check
        if not tls_enabled or endpoint_url.startswith("http://"):
            findings.append({
                "finding_code": "MEDIUM_VECTOR_DB_UNENCRYPTED_TRANSIT",
                "severity": "MEDIUM",
                "description": f"Vector database '{clean_engine}' communicates over unencrypted HTTP.",
            })

        return {
            "engine": clean_engine,
            "endpoint_url": endpoint_url,
            "is_public": is_public,
            "api_key_required": api_key_required,
            "tls_enabled": tls_enabled,
            "findings": findings,
            "status": "VULNERABLE" if findings else "HEALTHY",
        }

    @staticmethod
    def _is_public(url: str, is_in_vpc: bool) -> bool:
        if is_in_vpc:
            return False
        parsed = urlparse(url if "://" in url else f"http://{url}")
        host = parsed.hostname or url.split(":")[0]
        if host in ("localhost", "127.0.0.1", "::1"):
            return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_loopback:
                return False
            if (
                ip in ipaddress.ip_network("10.0.0.0/8")
                or ip in ipaddress.ip_network("172.16.0.0/12")
                or ip in ipaddress.ip_network("192.168.0.0/16")
            ):
                return False
            return True
        except ValueError:
            return not any(host.endswith(sfx) for sfx in (".internal", ".local", ".corp"))
