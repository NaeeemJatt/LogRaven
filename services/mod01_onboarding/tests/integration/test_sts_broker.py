"""Integration tests for STS AssumeRole Token Broker and Policy Simulator.

Covers:
- TC-MOD1-002: Credential caching & cache hit speed
- TC-MOD1-003: Policy simulation with missing permissions (DEGRADED)
- TC-MOD1-005: Chaos resilience on transient STS 503 errors
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from botocore.exceptions import ClientError

from services.mod01_onboarding.internal.sts_broker.token_cache import TokenCache
from services.mod01_onboarding.internal.sts_broker.aws_sts import STSAssumeRoleBroker
from services.mod01_onboarding.internal.validator.policy_simulator import PolicySimulator, REQUIRED_ACTIONS


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

    # Second call - cache hit (latency < 5ms)
    t0 = time.perf_counter()
    creds_2, cache_hit_2 = await broker.get_credentials(tenant_id, account_id, role_arn, ext_id)
    t1 = time.perf_counter()

    assert cache_hit_2
    assert creds_2["access_key_id"] == "AKIA_MOCK_KEY_123"
    assert mock_sts.assume_role.call_count == 1 # Did not call STS again!
    assert (t1 - t0) * 1000 < 15.0 # Sub-15ms response in pytest


@pytest.mark.asyncio
async def test_tc_mod1_003_policy_simulator_missing_permissions():
    """TC-MOD1-003: Simulate customer removing s3:GetEncryptionConfiguration.
    
    Returns status: DEGRADED, iom_ready: false, missing_permissions: ['s3:GetEncryptionConfiguration'].
    """
    mock_iam = MagicMock()
    
    # Simulate EvaluationResults where s3:GetEncryptionConfiguration is denied
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

    # Raise error twice, then succeed
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
    # Succeeded within 1.5s budget
    assert (t1 - t0) < 1.5


@pytest.mark.asyncio
async def test_token_cache_180s_expiration_margin():
    """Verify that credentials expiring in <= 180s are treated as expired."""
    cache = TokenCache()
    tenant_id = "tenant-margin"
    account_id = "account-margin"

    # Store creds expiring in 120s (within 180s margin)
    exp = datetime.now(timezone.utc) + timedelta(seconds=120)
    await cache.store_credentials(
        tenant_id=tenant_id,
        account_id=account_id,
        credentials={"access_key_id": "EXPIRING_SOON"},
        expiration=exp,
    )

    # Lookup should return None because it's in the 180s danger zone
    active = await cache.get_credentials(tenant_id, account_id)
    assert active is None

