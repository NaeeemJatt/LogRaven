"""Canonical URN Builder for Universal Multi-Cloud Asset Identification (FR-MOD2-02, TC-MOD2-002).

URN Format:
  urn:lograven:{provider}:{account_id}:{region}:{service}:{resource_type}/{resource_id}
"""

import re
from typing import Optional

# Canonical URN Specification Regular Expression
URN_REGEX = re.compile(
    r"^urn:lograven:(aws|azure|gcp|oci|alibaba|k8s|saas):[^:]+:[^:]+:[^:]+:[^/]+/.+$"
)

VALID_PROVIDERS = {"aws", "azure", "gcp", "oci", "alibaba", "k8s", "saas"}


def build_urn(
    provider: str,
    account_id: str,
    region: str,
    service: str,
    resource_type: str,
    resource_id: str,
) -> str:
    """Builds a deterministic, standardized Canonical URN for any cloud or container asset.
    
    Args:
        provider: aws, azure, gcp, oci, alibaba, k8s, saas
        account_id: 12-digit AWS account ID, Azure Subscription UUID, GCP Project ID, or cluster name
        region: AWS/Azure region (e.g. us-east-1, eastus) or 'global' for non-regional services
        service: cloud service identifier (e.g. s3, ec2, iam, storage, compute, keyvault)
        resource_type: resource category (e.g. aws_s3_bucket, ec2_instance, vault, deployment)
        resource_id: unique resource identifier or name
        
    Returns:
        Standardized Canonical URN string matching URN_REGEX
        
    Raises:
        ValueError if provider is invalid or any required segment is empty
    """
    prov = (provider or "").strip().lower()
    if prov not in VALID_PROVIDERS:
        raise ValueError(f"Invalid cloud provider '{provider}'. Must be one of {sorted(VALID_PROVIDERS)}")

    acct = str(account_id or "").strip()
    if not acct:
        raise ValueError("account_id cannot be empty")

    reg = (region or "").strip().lower() or "global"

    svc = (service or "").strip().lower()
    if not svc:
        raise ValueError("service cannot be empty")

    rtype = (resource_type or "").strip().lower()
    if not rtype:
        raise ValueError("resource_type cannot be empty")

    # Clean resource_id (strip leading slashes or redundant prefixes)
    rid = str(resource_id or "").strip()
    if not rid:
        raise ValueError("resource_id cannot be empty")
    while rid.startswith("/"):
        rid = rid[1:]

    urn = f"urn:lograven:{prov}:{acct}:{reg}:{svc}:{rtype}/{rid}"

    if not URN_REGEX.match(urn):
        raise ValueError(f"Generated URN '{urn}' does not conform to LogRaven URN specification")

    return urn


def parse_urn(urn: str) -> dict:
    """Parses a Canonical URN back into its discrete cloud metadata components."""
    if not URN_REGEX.match(urn):
        raise ValueError(f"URN '{urn}' does not conform to specification")

    parts = urn.split(":")
    # urn:lograven:{provider}:{account_id}:{region}:{service}:{resource_type}/{resource_id}
    provider = parts[2]
    account_id = parts[3]
    region = parts[4]
    service = parts[5]

    rest = ":".join(parts[6:])
    if "/" not in rest:
        raise ValueError(f"Invalid resource segment in URN: {rest}")

    resource_type, resource_id = rest.split("/", 1)

    return {
        "urn": urn,
        "provider": provider,
        "account_id": account_id,
        "region": region,
        "service": service,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }

