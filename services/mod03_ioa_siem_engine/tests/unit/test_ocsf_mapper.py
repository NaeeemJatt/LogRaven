"""Unit tests for OCSF v1.2 Multi-Cloud Normalization (TC-MOD3-001)."""

import pytest

from services.mod03_ioa_siem_engine.internal.parser.ocsf_mapper import OCSFMapper, _is_ip_external


def test_tc_mod3_001_ocsf_multi_cloud_mapping():
    """TC-MOD3-001: Feed raw AWS CloudTrail AssumeRole, Azure roleAssignments/write, and GCP SetIamPolicy.
    
    Pass Criteria: All 3 produce valid OCSF v1.2 structs with populated actor_user_arn,
    target_resource_urn, and read_only = 0.
    """
    tenant_id = "00000000-0000-0000-0000-000000000001"

    # 1. AWS CloudTrail AssumeRole
    aws_event = {
        "eventVersion": "1.08",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "AIDAEXAMPLEUSER",
            "arn": "arn:aws:iam::123456789012:user/developer-bob",
            "accountId": "123456789012",
            "userName": "developer-bob",
        },
        "eventTime": "2026-11-13T10:15:30Z",
        "eventSource": "sts.amazonaws.com",
        "eventName": "AssumeRole",
        "awsRegion": "us-east-1",
        "sourceIPAddress": "198.51.100.45",
        "requestParameters": {
            "roleArn": "arn:aws:iam::123456789012:role/SecurityAuditRole",
            "roleSessionName": "audit-session",
        },
        "readOnly": False,
    }

    aws_ocsf = OCSFMapper.map_event(aws_event, tenant_id=tenant_id, provider_hint="aws")
    assert aws_ocsf.provider == "aws"
    assert aws_ocsf.actor_user_arn == "arn:aws:iam::123456789012:user/developer-bob"
    assert aws_ocsf.read_only == 0
    assert "urn:lograven:aws:123456789012:global:iam:aws_iam_role/SecurityAuditRole" == aws_ocsf.target_resource_urn
    assert aws_ocsf.is_external_ip == 1

    # 2. Azure Activity Log roleAssignments/write
    azure_event = {
        "time": "2026-11-13T10:15:42Z",
        "subscriptionId": "sub-az-987654321",
        "resourceLocation": "eastus",
        "operationName": {
            "value": "Microsoft.Authorization/roleAssignments/write",
            "localizedValue": "Create role assignment",
        },
        "caller": "admin@contoso.onmicrosoft.com",
        "callerIpAddress": "203.0.113.19",
        "resourceId": "/subscriptions/sub-az-987654321/resourceGroups/rg-sec/providers/Microsoft.Authorization/roleAssignments/ra-999",
        "status": {"value": "Succeeded"},
    }

    az_ocsf = OCSFMapper.map_event(azure_event, tenant_id=tenant_id, provider_hint="azure")
    assert az_ocsf.provider == "azure"
    assert az_ocsf.actor_user_arn == "admin@contoso.onmicrosoft.com"
    assert az_ocsf.read_only == 0
    assert az_ocsf.target_resource_urn.startswith("urn:lograven:azure:sub-az-987654321:eastus:authorization:")
    assert az_ocsf.target_resource_urn.endswith("ra-999")
    assert az_ocsf.is_external_ip == 1

    # 3. GCP Cloud Audit Log SetIamPolicy
    gcp_event = {
        "timestamp": "2026-11-13T10:15:55Z",
        "resource": {
            "type": "project",
            "labels": {
                "project_id": "corp-production-gcp",
                "location": "us-central1",
            },
        },
        "protoPayload": {
            "methodName": "google.iam.v1.IAMPolicy.SetIamPolicy",
            "authenticationInfo": {
                "principalEmail": "sec-ops@corp-production-gcp.iam.gserviceaccount.com"
            },
            "requestMetadata": {
                "callerIp": "192.0.2.77"
            },
            "resourceName": "//cloudresourcemanager.googleapis.com/projects/corp-production-gcp",
            "status": {"code": 0},
        },
    }

    gcp_ocsf = OCSFMapper.map_event(gcp_event, tenant_id=tenant_id, provider_hint="gcp")
    assert gcp_ocsf.provider == "gcp"
    assert gcp_ocsf.actor_user_arn == "sec-ops@corp-production-gcp.iam.gserviceaccount.com"
    assert gcp_ocsf.read_only == 0
    assert gcp_ocsf.target_resource_urn.startswith("urn:lograven:gcp:corp-production-gcp:us-central1:")
    assert "corp-production-gcp" in gcp_ocsf.target_resource_urn
    assert gcp_ocsf.is_external_ip == 1


def test_ip_classification_external_vs_private():
    """Verifies private RFC1918 / loopback / link-local addresses are marked internal (0)."""
    assert _is_ip_external("10.0.4.15") == 0
    assert _is_ip_external("172.16.20.1") == 0
    assert _is_ip_external("192.168.1.100") == 0
    assert _is_ip_external("127.0.0.1") == 0
    assert _is_ip_external("169.254.169.254") == 0
    assert _is_ip_external("invalid-ip") == 0

    # Public/External routable IPs
    assert _is_ip_external("8.8.8.8") == 1
    assert _is_ip_external("185.220.101.4") == 1
    assert _is_ip_external("2607:f8b0:4005:805::200e") == 1

