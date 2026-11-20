# LogRaven — Cloud Asset Inventory & API Unit Tests

import pytest
import uuid
from datetime import datetime, timezone

from app.services.asset_discovery import (
    build_canonical_urn,
    strip_volatile_fields,
    compute_config_hash,
    normalize_raw_resource,
    _generate_baseline_assets,
)
from app.schemas.asset import (
    AssetResponse,
    AssetListResponse,
    AssetFiltersResponse,
    AssetSummaryResponse,
)


def test_build_canonical_urn():
    urn = build_canonical_urn("AWS", "123456789012", "us-east-1", "S3", "bucket", "corp-data")
    assert urn == "urn:lograven:aws:123456789012:us-east-1:s3:bucket/corp-data"

    # Test sanitization / casing
    urn_upper = build_canonical_urn("Azure", "Sub-123", "EastUS", "VirtualMachines", "VM", "ProdServer")
    assert urn_upper == "urn:lograven:azure:Sub-123:eastus:virtualmachines:vm/ProdServer"


def test_strip_volatile_fields_and_hash():
    config1 = {
        "bucket_name": "secure-vault",
        "encrypted": True,
        "ResponseMetadata": {"RequestId": "12345", "HTTPStatusCode": 200},
        "LastModified": "2026-11-19T00:00:00Z",
    }
    config2 = {
        "encrypted": True,
        "bucket_name": "secure-vault",
        "ResponseMetadata": {"RequestId": "67890", "HTTPStatusCode": 200},
        "LastModified": "2026-11-19T12:00:00Z",
    }

    clean1 = strip_volatile_fields(config1)
    clean2 = strip_volatile_fields(config2)

    assert "ResponseMetadata" not in clean1
    assert "LastModified" not in clean1
    assert clean1 == clean2

    # Deterministic SHA-256 hash
    hash1 = compute_config_hash(clean1)
    hash2 = compute_config_hash(clean2)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_normalize_raw_resource():
    raw_s3 = {
        "native_id": "test-bucket",
        "bucket_name": "test-bucket",
        "region": "us-east-1",
        "default_encryption": False,
        "tags": {"env": "dev"},
    }
    norm = normalize_raw_resource(raw_s3, "AWS", "123456789012", "S3")

    assert norm["urn"] == "urn:lograven:aws:123456789012:us-east-1:s3:bucket/test-bucket"
    assert norm["provider"] == "AWS"
    assert norm["service"] == "S3"
    assert norm["compliance_status"] == "NON_COMPLIANT"
    assert norm["failing_rule_count"] == 1


def test_generate_baseline_assets():
    tenant_id = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    assets = _generate_baseline_assets(None, tenant_id, now_utc)

    assert len(assets) >= 10
    services = {a["service"] for a in assets}
    assert "IAM" in services
    assert "S3" in services
    assert "EC2" in services
    assert "SECURITY_GROUP" in services
    assert "LOAD_BALANCER" in services
    assert "API_GATEWAY" in services
    assert "LOG_GROUP" in services
    assert "LAMBDA" in services
    assert "VPC" in services
    assert "RDS" in services
    assert "KMS" in services

    # Verify separate services for EC2, Security Groups, and Load Balancers
    ec2_types = {a["resource_type"] for a in assets if a["service"] == "EC2"}
    assert "aws_ec2_instance" in ec2_types
    assert "aws_ec2_security_group" not in ec2_types  # Security groups are separate

    sg_types = {a["resource_type"] for a in assets if a["service"] == "SECURITY_GROUP"}
    assert "aws_security_group_security_group" in sg_types

    lb_types = {a["resource_type"] for a in assets if a["service"] == "LOAD_BALANCER"}
    assert "aws_load_balancer_load_balancer" in lb_types

    # Verify canonical URN format on all generated assets
    for a in assets:
        assert a["urn"].startswith("urn:lograven:")
        assert len(a["config_sha256"]) == 64
        assert a["compliance_status"] in ("COMPLIANT", "NON_COMPLIANT")
