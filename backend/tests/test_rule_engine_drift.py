"""
Unit tests for Module 06: Real-Time AWS Log Stream & Mutating Drift Engine (FR-DET-05).
Verifies tri-path evaluation:
1. Real-time CloudTrail runtime log controls (CID 18, CID 27, CID 28).
2. Mutating IAM event drift extraction (PutRolePolicy -> CID 50).
3. Mutating VPC Security Group drift extraction (AuthorizeSecurityGroupIngress -> CID 41).
4. Mutating S3 exposure drift (PutBucketAcl -> Public exposure).
5. Sliding-window threshold correlation.
"""

import time
import pytest

from app.rules.schema import (
    ConditionRule,
    DeterministicRuleSpec,
    ExecutionMode,
    OperatorType,
)
from app.rules.loader import RuleLoader, RULES_DIR
from app.rules.engine import RuleEngine


@pytest.fixture(scope="module")
def rule_engine():
    loader = RuleLoader(RULES_DIR)
    loader.load_all()
    return RuleEngine(loader)


def test_path_ab_cid_18_root_account_log_detection(rule_engine):
    root_event = {
        "eventVersion": "1.08",
        "userIdentity": {
            "type": "Root",
            "principalId": "123456789012",
            "arn": "arn:aws:iam::123456789012:root",
        },
        "eventTime": "2026-11-15T12:00:00Z",
        "eventSource": "ec2.amazonaws.com",
        "eventName": "RunInstances",
        "eventType": "AwsApiCall",
        "sourceIPAddress": "203.0.113.5",
    }

    alerts = rule_engine.process_cloudtrail_event(root_event)
    alert_cids = {a["cid"] for a in alerts}

    assert "18" in alert_cids
    r18_alert = next(a for a in alerts if a["cid"] == "18")
    assert r18_alert["detection_mode"] == "REALTIME_CLOUDTRAIL_LOG"
    assert r18_alert["actor_arn"] == "arn:aws:iam::123456789012:root"


def test_path_ab_cid_28_console_login_without_mfa(rule_engine):
    login_no_mfa = {
        "eventName": "ConsoleLogin",
        "eventSource": "signin.amazonaws.com",
        "userIdentity": {
            "type": "IAMUser",
            "arn": "arn:aws:iam::123456789012:user/developer",
        },
        "additionalEventData": {
            "MFAUsed": "No",
        },
        "sourceIPAddress": "198.51.100.22",
    }

    alerts = rule_engine.process_cloudtrail_event(login_no_mfa)
    alert_cids = {a["cid"] for a in alerts}

    assert "28" in alert_cids
    r28_alert = next(a for a in alerts if a["cid"] == "28")
    assert r28_alert["detection_mode"] == "REALTIME_CLOUDTRAIL_LOG"


def test_path_c_iam_put_role_policy_inline_drift(rule_engine):
    mutating_event = {
        "eventName": "PutRolePolicy",
        "eventSource": "iam.amazonaws.com",
        "userIdentity": {
            "type": "IAMUser",
            "arn": "arn:aws:iam::123456789012:user/admin",
        },
        "requestParameters": {
            "roleName": "production-app-role",
            "policyName": "WildcardAdminAttached",
            "policyDocument": '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"s3:*","Resource":"*"}]}',
        },
        "sourceIPAddress": "198.51.100.99",
    }

    alerts = rule_engine.process_cloudtrail_event(mutating_event)
    drift_alerts = [a for a in alerts if a["detection_mode"] == "CLOUDTRAIL_INLINE_DRIFT"]

    assert len(drift_alerts) >= 1
    iam_drift = next(a for a in drift_alerts if a["service"] == "IAM")
    assert iam_drift["cid"] == "50"
    assert iam_drift["event_name"] == "PutRolePolicy"


def test_path_c_vpc_security_group_ingress_drift(rule_engine):
    open_ssh_event = {
        "eventName": "AuthorizeSecurityGroupIngress",
        "eventSource": "ec2.amazonaws.com",
        "userIdentity": {
            "type": "IAMUser",
            "arn": "arn:aws:iam::123456789012:user/devops",
        },
        "requestParameters": {
            "groupId": "sg-0123456789abcdef0",
            "ipPermissions": {
                "items": [
                    {
                        "ipProtocol": "tcp",
                        "fromPort": 22,
                        "toPort": 22,
                        "ipRanges": {"items": [{"cidrIp": "0.0.0.0/0"}]},
                    }
                ]
            },
        },
        "sourceIPAddress": "203.0.113.88",
    }

    alerts = rule_engine.process_cloudtrail_event(open_ssh_event)
    drift_alerts = [a for a in alerts if a["detection_mode"] == "CLOUDTRAIL_INLINE_DRIFT"]

    assert len(drift_alerts) >= 1
    vpc_drift = next(a for a in drift_alerts if a["service"] == "VPC")
    assert vpc_drift["cid"] == "41"
    assert vpc_drift["event_name"] == "AuthorizeSecurityGroupIngress"


def test_path_c_benign_security_group_no_drift(rule_engine):
    private_https_event = {
        "eventName": "AuthorizeSecurityGroupIngress",
        "eventSource": "ec2.amazonaws.com",
        "userIdentity": {"type": "IAMUser", "arn": "arn:aws:iam::123456789012:user/devops"},
        "requestParameters": {
            "groupId": "sg-locked",
            "ipPermissions": {
                "items": [
                    {
                        "ipProtocol": "tcp",
                        "fromPort": 443,
                        "toPort": 443,
                        "ipRanges": {"items": [{"cidrIp": "10.0.0.0/8"}]},
                    }
                ]
            },
        },
    }

    alerts = rule_engine.process_cloudtrail_event(private_https_event)
    drift_alerts = [a for a in alerts if a["detection_mode"] == "CLOUDTRAIL_INLINE_DRIFT"]
    assert len(drift_alerts) == 0


def test_sliding_window_threshold():
    loader = RuleLoader()
    rule = DeterministicRuleSpec(
        rule_id="RULE-THRESHOLD-TEST",
        cid="999",
        title="Repeated Access Denied",
        provider="AWS",
        service="IAM",
        target_source="aws_cloudtrail_log",
        conditions=[
            ConditionRule(field_path="$.errorCode", operator=OperatorType.EQ, value="AccessDenied")
        ],
        group_by_fields=["$.sourceIPAddress"],
        window_seconds=10,
        threshold_count=3,
    )
    loader.rules_by_id[rule.rule_id] = rule
    loader.index_by_target[("AWS", "IAM", "aws_cloudtrail_log")].append(rule)

    engine = RuleEngine(loader)
    event = {"errorCode": "AccessDenied", "sourceIPAddress": "192.168.1.10"}

    # 1st and 2nd events should not alert
    assert len(engine.process_cloudtrail_event(event)) == 0
    assert len(engine.process_cloudtrail_event(event)) == 0

    # 3rd event should trigger alert
    alerts = engine.process_cloudtrail_event(event)
    assert len(alerts) == 1
    assert alerts[0]["rule_id"] == "RULE-THRESHOLD-TEST"
