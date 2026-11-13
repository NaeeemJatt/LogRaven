"""Unit tests for Multi-Cloud Template Synthesis Engine (TC-MOD1-001)."""

import yaml
import pytest
from services.mod01_onboarding.internal.generators.aws_cloudformation import (
    generate_aws_stackset,
    generate_single_account_cf,
)
from services.mod01_onboarding.internal.generators.terraform_hcl import (
    generate_aws_terraform,
    generate_azure_terraform,
    generate_gcp_terraform,
)
from services.mod01_onboarding.internal.generators.azure_bicep import generate_azure_bicep
from services.mod01_onboarding.internal.generators.gcp_deployment_manager import generate_gcp_deployment_manager


def test_tc_mod1_001_aws_stackset_generation():
    """TC-MOD1-001: GenerateAWSStackSet(tenantID, extID, regions) with 3 regions.
    
    Output YAML parses as valid CloudFormation; sts:ExternalId matches;
    events:PutEvents restricted to arn:aws:events:*:*:event-bus/lr-*.
    """
    tenant_id = "tenant-test-001"
    external_id = "lr-ext-1234567890abcdef1234567890abcdef"
    regions = ["us-east-1", "eu-west-1", "ap-south-1"]

    cf_yaml = generate_aws_stackset(tenant_id=tenant_id, external_id=external_id, regions=regions)
    parsed = yaml.safe_load(cf_yaml)

    assert parsed is not None
    assert parsed["AWSTemplateFormatVersion"] == "2010-09-09"
    assert parsed["Parameters"]["ExternalId"]["Default"] == external_id
    assert parsed["Parameters"]["TargetRegions"]["Default"] == "us-east-1, eu-west-1, ap-south-1"

    # Verify IAM Role trust policy has ExternalId
    reader_role = parsed["Resources"]["LogRavenReaderRole"]["Properties"]
    trust_stmt = reader_role["AssumeRolePolicyDocument"]["Statement"][0]
    assert trust_stmt["Action"] == "sts:AssumeRole"
    assert trust_stmt["Condition"]["StringEquals"]["sts:ExternalId"]["Ref"] == "ExternalId"

    # Verify events:PutEvents restriction
    policies = reader_role["Policies"]
    put_events_stmt = policies[0]["PolicyDocument"]["Statement"][0]
    assert "events:PutEvents" in put_events_stmt["Action"]
    assert "lr-ingest-tenant-test-001" in str(put_events_stmt["Resource"])

    # Verify regional events forwarder role
    events_role = parsed["Resources"]["LogRavenEventsRole"]["Properties"]
    ev_stmt = events_role["Policies"][0]["PolicyDocument"]["Statement"][0]
    assert ev_stmt["Resource"] == "arn:aws:events:*:*:event-bus/lr-*"


def test_single_account_cf_generation():
    tenant_id = "tenant-002"
    external_id = "lr-ext-abcdefabcdefabcdefabcdefabcdef"
    cf_yaml = generate_single_account_cf(tenant_id, external_id)
    parsed = yaml.safe_load(cf_yaml)

    assert parsed["AWSTemplateFormatVersion"] == "2010-09-09"
    assert parsed["Parameters"]["ExternalId"]["Default"] == external_id
    assert "LogRavenReaderRole" in parsed["Resources"]
    assert "LogRavenTelemetryRule" in parsed["Resources"]


def test_terraform_hcl_generators():
    aws_tf = generate_aws_terraform("tenant-003", "lr-ext-999")
    assert 'resource "aws_iam_role" "lograven_reader"' in aws_tf
    assert 'lr-ext-999' in aws_tf
    assert 'arn:aws:events:us-east-1:112233445566:event-bus/lr-ingest-tenant-003' in aws_tf

    azure_tf = generate_azure_terraform("tenant-003", "sub-123", "sp-456")
    assert 'scope                = "/subscriptions/sub-123"' in azure_tf
    assert 'role_definition_name = "Security Reader"' in azure_tf

    gcp_tf = generate_gcp_terraform("tenant-003", "proj-789")
    assert 'resource "google_service_account" "lograven_reader"' in gcp_tf
    assert 'roles/iam.securityReviewer' in gcp_tf


def test_azure_bicep_and_gcp_deployment_manager():
    bicep = generate_azure_bicep("tenant-004", "sp-id-abc")
    assert "Microsoft.Authorization/roleAssignments@2022-04-01" in bicep
    assert "sp-id-abc" in bicep

    gcp_yaml = generate_gcp_deployment_manager("tenant-004", "proj-xyz")
    parsed = yaml.safe_load(gcp_yaml)
    assert len(parsed["resources"]) >= 3
    assert parsed["resources"][0]["name"] == "lograven-cspm-reader"

