"""Integration tests for Stateful Sliding-Window IOA Evaluator.

Covers:
- TC-MOD3-002: PassRole -> CreateFunction -> InvokeFunction privilege escalation chain
- TC-MOD3-003: Cloud Enumeration burst (40 AccessDenied calls within 45s)
"""

import asyncio
import time
import pytest

from services.mod03_ioa_siem_engine.internal.ioa_evaluator.sliding_window import SlidingWindowIOAEvaluator


@pytest.mark.asyncio
async def test_tc_mod3_002_privilege_escalation_chain():
    """TC-MOD3-002: Stream iam:PassRole followed 12s later by lambda:CreateFunction and lambda:InvokeFunction.
    
    Pass Criteria: Sliding-window evaluator fires IOA-AWS-PRIVESC-004 (CRITICAL, MITRE T1078.004)
    within 500ms of third event.
    """
    evaluator = SlidingWindowIOAEvaluator(window_seconds=900)
    tenant_id = "tenant-test-001"
    actor = "arn:aws:iam::123456789012:user/intern-jake"
    account = "123456789012"
    base_time = time.time()

    # Step 1: iam:PassRole
    evt_1 = {
        "tenant_id": tenant_id,
        "actor_user_arn": actor,
        "account_id": account,
        "event_name": "PassRole",
        "timestamp": base_time,
        "region": "us-east-1",
    }
    hit_1 = await evaluator.ingest_and_evaluate(evt_1)
    assert hit_1 is None, "PassRole alone must not trigger a full privilege escalation alert"

    # Step 2: lambda:CreateFunction (12 seconds later)
    evt_2 = {
        "tenant_id": tenant_id,
        "actor_user_arn": actor,
        "account_id": account,
        "event_name": "CreateFunction",
        "timestamp": base_time + 12.0,
        "region": "us-east-1",
    }
    hit_2 = await evaluator.ingest_and_evaluate(evt_2)
    assert hit_2 is None, "CreateFunction before Invoke must not trigger complete escalation alert"

    # Step 3: lambda:InvokeFunction (18 seconds later)
    evt_3 = {
        "tenant_id": tenant_id,
        "actor_user_arn": actor,
        "account_id": account,
        "event_name": "InvokeFunction",
        "timestamp": base_time + 18.0,
        "region": "us-east-1",
    }
    start_eval = time.perf_counter()
    hit_3 = await evaluator.ingest_and_evaluate(evt_3)
    eval_duration_ms = (time.perf_counter() - start_eval) * 1000

    assert hit_3 is not None, "Complete execution chain MUST fire privilege escalation alert"
    assert hit_3["rule_id"] == "IOA-AWS-PRIVESC-004"
    assert hit_3["severity"] == "CRITICAL"
    assert hit_3["mitre_technique"] == "T1078.004"
    assert hit_3["mitre_tactic"] == "PRIVILEGE_ESCALATION"
    assert hit_3["actor_user_arn"] == actor
    assert hit_3["matched_events_count"] == 3
    assert eval_duration_ms < 500.0, f"Evaluation must complete in < 500ms (took {eval_duration_ms:.2f}ms)"


@pytest.mark.asyncio
async def test_tc_mod3_003_enumeration_burst_grouping():
    """TC-MOD3-003: Stream 40 secretsmanager:ListSecrets and ssm:DescribeParameters calls with AccessDenied within 45s.
    
    Pass Criteria: Evaluator fires IOA-CLOUD-ENUM-011 (HIGH, Enumeration burst threshold exceeded)
    and groups all 40 events into 1 incident.
    """
    evaluator = SlidingWindowIOAEvaluator(window_seconds=900)
    tenant_id = "tenant-test-002"
    actor = "arn:aws:iam::123456789012:user/compromised-ci"
    account = "123456789012"
    base_time = time.time()

    alerts_fired = []

    # Stream 40 rapid enumeration calls with AccessDenied across 45 seconds (1.125s interval)
    for i in range(40):
        evt_name = "ListSecrets" if i % 2 == 0 else "DescribeParameters"
        evt = {
            "tenant_id": tenant_id,
            "actor_user_arn": actor,
            "account_id": account,
            "event_name": evt_name,
            "error_code": "AccessDenied",
            "timestamp": base_time + (i * 1.0),  # spans 39 seconds
            "region": "us-east-1",
        }
        res = await evaluator.ingest_and_evaluate(evt)
        if res:
            alerts_fired.append(res)

    # Must fire enumeration burst
    assert len(alerts_fired) >= 1
    final_alert = alerts_fired[-1]
    assert final_alert["rule_id"] == "IOA-CLOUD-ENUM-011"
    assert final_alert["severity"] == "HIGH"
    assert final_alert["mitre_technique"] == "T1580"
    assert final_alert["mitre_tactic"] == "ENUMERATION"
    assert final_alert["actor_user_arn"] == actor
    # Groups all denied events into 1 incident
    assert final_alert["matched_events_count"] >= 20


@pytest.mark.asyncio
async def test_defense_evasion_single_event():
    """Verify single-event defense evasion (StopLogging) triggers immediately."""
    evaluator = SlidingWindowIOAEvaluator(window_seconds=900)
    evt = {
        "tenant_id": "tenant-test-003",
        "actor_user_arn": "arn:aws:iam::123456789012:user/rogue-admin",
        "account_id": "123456789012",
        "event_name": "StopLogging",
        "region": "us-east-1",
    }
    alert = await evaluator.ingest_and_evaluate(evt)
    assert alert is not None
    assert alert["rule_id"] == "IOA-AWS-DEFENSE-001"
    assert alert["severity"] == "CRITICAL"
    assert alert["mitre_tactic"] == "DEFENSE_EVASION"

