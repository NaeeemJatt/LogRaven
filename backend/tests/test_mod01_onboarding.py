"""Module 01: Multi-Cloud Onboarding & Trust Broker Comprehensive Tests."""

import logging
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from botocore.exceptions import ClientError
import yaml

from services.mod01_onboarding.internal.crypto import (
    generate_external_id,
    encrypt_external_id,
    decrypt_external_id,
)
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
from services.mod01_onboarding.internal.sts_broker.token_cache import TokenCache
from services.mod01_onboarding.internal.sts_broker.aws_sts import STSAssumeRoleBroker
from services.mod01_onboarding.internal.validator.policy_simulator import PolicySimulator, REQUIRED_ACTIONS


# ── TC-MOD1-001: CloudFormation & Template Synthesis ─────────────────────

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


def test_template_generators_all_clouds():
    """Verify Terraform, Bicep, and GCP deployment manager synthesis."""
    aws_tf = generate_aws_terraform("tenant-003", "lr-ext-999")
    assert 'resource "aws_iam_role" "lograven_reader"' in aws_tf
    assert 'lr-ext-999' in aws_tf

    azure_tf = generate_azure_terraform("tenant-003", "sub-123", "sp-456")
    assert 'role_definition_name = "Security Reader"' in azure_tf

    gcp_tf = generate_gcp_terraform("tenant-003", "proj-789")
    assert 'roles/iam.securityReviewer' in gcp_tf

    bicep = generate_azure_bicep("tenant-004", "sp-id-abc")
    assert "Microsoft.Authorization/roleAssignments@2022-04-01" in bicep

    gcp_dm = generate_gcp_deployment_manager("tenant-004", "proj-xyz")
    parsed_gcp = yaml.safe_load(gcp_dm)
    assert len(parsed_gcp["resources"]) >= 3


# ── TC-MOD1-002: Token Caching & Performance ─────────────────────────────

@pytest.mark.asyncio
async def test_tc_mod1_002_sts_broker_caching():
    """TC-MOD1-002: Call Broker.GetCredentials; second call within 10m hits cache."""
    mock_sts = MagicMock()
    exp_time = datetime.now(timezone.utc) + timedelta(minutes=60)
    mock_sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIA_MOCK_KEY_123",
            "SecretAccessKey": "MOCK_SECRET_XYZ",
            "SessionToken": "MOCK_SESSION_TOKEN_ABC",
            "Expiration": exp_time,
        }
    }

    cache = TokenCache()
    broker = STSAssumeRoleBroker(cache=cache, sts_client=mock_sts)

    tenant_id = "tenant-int-001"
    account_id = "111222333444"
    role_arn = "arn:aws:iam::111222333444:role/LogRavenCSPMReader"
    ext_id = "lr-ext-abc12345"

    # First call - cache miss
    creds_1, cache_hit_1 = await broker.get_credentials(tenant_id, account_id, role_arn, ext_id)
    assert not cache_hit_1
    assert creds_1["access_key_id"] == "AKIA_MOCK_KEY_123"
    assert mock_sts.assume_role.call_count == 1

    # Second call - cache hit
    t0 = time.perf_counter()
    creds_2, cache_hit_2 = await broker.get_credentials(tenant_id, account_id, role_arn, ext_id)
    t1 = time.perf_counter()

    assert cache_hit_2
    assert creds_2["access_key_id"] == "AKIA_MOCK_KEY_123"
    assert mock_sts.assume_role.call_count == 1
    assert (t1 - t0) * 1000 < 15.0


# ── TC-MOD1-003: Policy Simulator & Missing Permissions ──────────────────

@pytest.mark.asyncio
async def test_tc_mod1_003_policy_simulator_missing_permissions():
    """TC-MOD1-003: Simulate customer removing s3:GetEncryptionConfiguration."""
    mock_iam = MagicMock()
    eval_results = []
    for action in REQUIRED_ACTIONS:
        decision = "denied" if action == "s3:GetEncryptionConfiguration" else "allowed"
        eval_results.append({
            "EvalActionName": action,
            "EvalDecision": decision,
        })
    mock_iam.simulate_principal_policy.return_value = {
        "EvaluationResults": eval_results
    }

    simulator = PolicySimulator(iam_client=mock_iam)
    res = await simulator.verify_permissions(
        role_arn="arn:aws:iam::123456789012:role/LogRavenCSPMReader",
        actions_to_test=REQUIRED_ACTIONS,
    )

    assert res["status"] == "DEGRADED"
    assert res["iom_ready"] is False
    assert res["ioa_stream_ready"] is True
    assert "s3:GetEncryptionConfiguration" in res["missing_permissions"]


# ── TC-MOD1-004: Confused Deputy Simulation ──────────────────────────────

@pytest.mark.asyncio
async def test_tc_mod1_004_confused_deputy_blocked(caplog):
    """TC-MOD1-004: Confused-Deputy Simulation."""
    mock_sts = MagicMock()
    error_response = {
        "Error": {
            "Code": "AccessDenied",
            "Message": "User is not authorized to perform: sts:AssumeRole",
        }
    }
    mock_sts.assume_role.side_effect = ClientError(error_response, "AssumeRole")

    broker = STSAssumeRoleBroker(cache=TokenCache(), sts_client=mock_sts)

    tenant_b_id = "tenant-b-attacker"
    tenant_a_role = "arn:aws:iam::tenant-a:role/LogRavenCSPMReader"
    tenant_b_ext_id = "lr-ext-tenant-b-secret-external-id"

    with caplog.at_level(logging.WARNING):
        with pytest.raises(ClientError) as exc_info:
            await broker.get_credentials(
                tenant_id=tenant_b_id,
                account_id="account-attacker",
                role_arn=tenant_a_role,
                external_id=tenant_b_ext_id,
            )

        assert exc_info.value.response["Error"]["Code"] == "AccessDenied"
        assert "SEC_CONFUSED_DEPUTY_BLOCKED" in caplog.text


# ── TC-MOD1-005: Chaos Resilience ────────────────────────────────────────

@pytest.mark.asyncio
async def test_tc_mod1_005_chaos_sts_transient_failure_recovery():
    """TC-MOD1-005: Inject 503 ServiceUnavailable on first 2 calls; succeeds on attempt 3."""
    mock_sts = MagicMock()
    exp_time = datetime.now(timezone.utc) + timedelta(minutes=60)
    
    error_response = {
        "Error": {
            "Code": "ServiceUnavailable",
            "Message": "AWS STS temporary overload",
        }
    }
    transient_exc = ClientError(error_response, "AssumeRole")

    mock_sts.assume_role.side_effect = [
        transient_exc,
        transient_exc,
        {
            "Credentials": {
                "AccessKeyId": "AKIA_RECOVERED_KEY",
                "SecretAccessKey": "SECRET_RECOVERED",
                "SessionToken": "SESSION_RECOVERED",
                "Expiration": exp_time,
            }
        },
    ]

    cache = TokenCache()
    broker = STSAssumeRoleBroker(cache=cache, sts_client=mock_sts)

    t0 = time.perf_counter()
    creds, cache_hit = await broker.get_credentials(
        "tenant-chaos", "account-chaos", "arn:aws:iam::123:role/Reader", "lr-ext-chaos"
    )
    t1 = time.perf_counter()

    assert not cache_hit
    assert creds["access_key_id"] == "AKIA_RECOVERED_KEY"
    assert mock_sts.assume_role.call_count == 3
    assert (t1 - t0) < 1.5


# ── Cryptography & Expiration Margin ─────────────────────────────────────

def test_crypto_external_id_encryption():
    ext = generate_external_id()
    assert ext.startswith("lr-ext-")
    enc = encrypt_external_id(ext)
    dec = decrypt_external_id(enc)
    assert dec == ext


@pytest.mark.asyncio
async def test_token_cache_180s_margin():
    cache = TokenCache()
    exp = datetime.now(timezone.utc) + timedelta(seconds=120)
    await cache.store_credentials("t-1", "a-1", {"access_key_id": "EXPIRING"}, exp)
    active = await cache.get_credentials("t-1", "a-1")
    assert active is None

