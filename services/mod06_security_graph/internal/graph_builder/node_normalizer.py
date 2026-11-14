"""6-Domain Cloud Insights Node Normalizer (PRD-MOD-06, FR-MOD6-01).

Normalizes cloud resources and security telemetry into unified graph domain schemas:
1. COMPUTE (EC2, EKS Pods, Lambda, Azure VMs, GCE Instances)
2. STORAGE (S3, EBS, GCS, Azure Blob)
3. NETWORK (Security Groups, VPC Route Tables, IGWs, Load Balancers)
4. IDENTITY (IAM Roles, IAM Users, Service Accounts, Managed Identities)
5. VULNERABILITY (CVEs, Unpatched packages from Mod 04 / Mod 05)
6. DATA (Crown Jewels, Databases with PII/PCI/HIPAA from Mod 08 DSPM)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SecurityDomain(str, Enum):
    COMPUTE = "COMPUTE"
    STORAGE = "STORAGE"
    NETWORK = "NETWORK"
    IDENTITY = "IDENTITY"
    VULNERABILITY = "VULNERABILITY"
    DATA = "DATA"


@dataclass
class NormalizedNode:
    id: str
    domain: SecurityDomain
    label: str
    provider: str = "aws"
    is_internet_facing: bool = False
    truerisk_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedEdge:
    id: str
    source_id: str
    target_id: str
    relationship: str
    remediation_friction: float = 1.0
    is_attack_path: bool = False


class NodeNormalizer:
    """Transforms multi-cloud assets and telemetry into normalized 6-domain graph entities."""

    @staticmethod
    def normalize_compute(
        asset_urn: str,
        name: str,
        provider: str = "aws",
        is_public: bool = False,
        cve_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NormalizedNode:
        return NormalizedNode(
            id=asset_urn,
            domain=SecurityDomain.COMPUTE,
            label=name,
            provider=provider,
            is_internet_facing=is_public,
            metadata={
                "cve_count": cve_count,
                **(metadata or {}),
            },
        )

    @staticmethod
    def normalize_network(
        sg_id: str,
        name: str,
        provider: str = "aws",
        has_open_ingress: bool = False,
        open_ports: Optional[List[int]] = None,
    ) -> NormalizedNode:
        return NormalizedNode(
            id=sg_id,
            domain=SecurityDomain.NETWORK,
            label=name,
            provider=provider,
            is_internet_facing=has_open_ingress,
            metadata={
                "open_ports": open_ports or [],
                "has_open_ingress": has_open_ingress,
            },
        )

    @staticmethod
    def normalize_identity(
        role_arn: str,
        name: str,
        provider: str = "aws",
        is_admin: bool = False,
        permissions: Optional[List[str]] = None,
    ) -> NormalizedNode:
        return NormalizedNode(
            id=role_arn,
            domain=SecurityDomain.IDENTITY,
            label=name,
            provider=provider,
            metadata={
                "is_admin": is_admin,
                "permissions": permissions or [],
            },
        )

    @staticmethod
    def normalize_crown_jewel(
        resource_id: str,
        name: str,
        domain: SecurityDomain = SecurityDomain.DATA,
        provider: str = "aws",
        has_pii: bool = True,
        classification: str = "PII_PCI_HIPAA",
    ) -> NormalizedNode:
        return NormalizedNode(
            id=resource_id,
            domain=domain,
            label=name,
            provider=provider,
            metadata={
                "is_crown_jewel": True,
                "has_pii": has_pii,
                "data_classification": classification,
            },
        )
