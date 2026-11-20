# LogRaven — Module 09: Comprehensive Deterministic CSPM & AWS Log Engine Verification Suite
# Directly implements the complete verification and benchmarking requirements from Section 8 of the design specification.
# Tests:
#   1. CID 41: SSH (port 22) open-world 0.0.0.0/0 & ::/0 detection
#   2. CID 42: RDP (port 3389) open-world ingress detection
#   3. CID 50: IAM AST wildcard static configuration evaluation
#   4. CID 50: CloudTrail inline mutating drift extraction (Path C: PutRolePolicy)
#   5. S3 Bucket SSE & Public Access Block compliance evaluation
#   6. CloudTrail runtime log controls (CID 18, 27–40 sliding windows & events)
#   7. Deterministic Compliance Grader weighted policy & mandate rollups
#   8. Multi-Cloud catalog and rule coverage (AWS, Azure, GCP, OCI: 1,565 controls)
#   9. Sub-millisecond performance benchmark (< 1ms per rule evaluation)
#  10. End-to-End FastAPI compliance audit pipeline

from __future__ import annotations

import json
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.collectors.aws_collector import AWSStateAndLogCollector
from app.compliance.deterministic_grader import DeterministicComplianceGrader, WEIGHTS
from app.compliance.frameworks.base import (
    get_mandate,
    get_policy,
    list_mandates,
    list_policies,
)
from app.main import app
from app.rules.engine import RuleEngine
from app.rules.evaluator import evaluate_rule
from app.rules.loader import RuleLoader


# ── Pytest Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def rule_loader() -> RuleLoader:
    loader = RuleLoader()
    loader.load_all()
    return loader


@pytest.fixture(scope="module")
def rule_engine(rule_loader: RuleLoader) -> RuleEngine:
    return RuleEngine(loader=rule_loader)


@pytest.fixture(scope="module")
def grader(rule_loader: RuleLoader) -> DeterministicComplianceGrader:
    return DeterministicComplianceGrader(loader=rule_loader)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# ── 1. CID 41: SSH Open World Detection ──────────────────────────────────────


def test_cid_41_ssh_open_world_detection(rule_loader: RuleLoader):
    rule = rule_loader.get_rule_by_cid("41")
    assert rule is not None, "CID 41 rule must be loaded in RuleLoader"
    assert rule.service.upper() in ("VPC", "EC2")

    # Case A: Compliant SG (Port 22 restricted to corporate RFC 1918 CIDR)
    compliant_sg = {
        "GroupId": "sg-secure-ssh",
        "IpPermissions": [
            {
                "FromPort": 22,
                "ToPort": 22,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "10.0.0.0/8"}],
                "Ipv6Ranges": [],
            }
        ],
    }
    assert evaluate_rule(compliant_sg, rule) is False, "Restricted SSH CIDR must not trigger violation"

    # Case B: Insecure SG with IPv4 0.0.0.0/0 on port 22
    insecure_sg_ipv4 = {
        "GroupId": "sg-insecure-ipv4",
        "IpPermissions": [
            {
                "FromPort": 22,
                "ToPort": 22,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                "Ipv6Ranges": [],
            }
        ],
    }
    assert evaluate_rule(insecure_sg_ipv4, rule) is True, "Open IPv4 0.0.0.0/0 must trigger CID 41 violation"

    # Case C: Insecure SG with IPv6 ::/0 on port 22
    insecure_sg_ipv6 = {
        "GroupId": "sg-insecure-ipv6",
        "IpPermissions": [
            {
                "FromPort": 22,
                "ToPort": 22,
                "IpProtocol": "tcp",
                "IpRanges": [],
                "Ipv6Ranges": [{"CidrIpv6": "::/0"}],
            }
        ],
    }
    assert evaluate_rule(insecure_sg_ipv6, rule) is True, "Open IPv6 ::/0 must trigger CID 41 violation"


# ── 2. CID 42: RDP Open World Detection ──────────────────────────────────────


def test_cid_42_rdp_open_world_detection(rule_loader: RuleLoader):
    rule = rule_loader.get_rule_by_cid("42")
    assert rule is not None, "CID 42 rule must be loaded in RuleLoader"

    # Compliant: Port 3389 restricted
    compliant_sg = {
        "GroupId": "sg-internal-rdp",
        "IpPermissions": [
            {
                "FromPort": 3389,
                "ToPort": 3389,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "172.16.0.0/12"}],
            }
        ],
    }
    assert evaluate_rule(compliant_sg, rule) is False

    # Insecure: Port 3389 open to world
    insecure_sg = {
        "GroupId": "sg-open-rdp",
        "IpPermissions": [
            {
                "FromPort": 3389,
                "ToPort": 3389,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ],
    }
    assert evaluate_rule(insecure_sg, rule) is True


# ── 3. CID 50: IAM AST Wildcard Static Configuration ────────────────────────


def test_cid_50_iam_ast_wildcard_static_eval(rule_loader: RuleLoader):
    rule = rule_loader.get_rule_by_cid("50")
    assert rule is not None, "CID 50 rule must be loaded in RuleLoader"
    assert rule.service.upper() == "IAM"

    # Case A: Least privilege role (s3:GetObject on specific bucket)
    least_priv_role = {
        "RoleName": "S3ReaderRole",
        "PolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::audit-bucket/*",
                }
            ],
        },
        "PolicyDocuments": [
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "s3:GetObject",
                        "Resource": "arn:aws:s3:::audit-bucket/*",
                    }
                ],
            }
        ],
    }
    assert evaluate_rule(least_priv_role, rule) is False, "Scoped IAM policy must not violate CID 50"

    # Case B: Dangerous AdministratorAccess wildcard policy (Action: *, Resource: *)
    admin_wildcard_role = {
        "RoleName": "AdminWildcardRole",
        "PolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "*",
                    "Resource": "*",
                }
            ],
        },
        "PolicyDocuments": [
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "*",
                        "Resource": "*",
                    }
                ],
            }
        ],
    }
    assert evaluate_rule(admin_wildcard_role, rule) is True, "Wildcard *:* statement must trigger CID 50 violation"


# ── 4. CID 50: CloudTrail Inline Mutating Drift ──────────────────────────────


def test_cid_50_cloudtrail_mutating_drift(rule_engine: RuleEngine):
    # Simulated CloudTrail event: attacker attaches inline policy with Action:* and Resource:*
    drift_event = {
        "eventID": "evt-mutating-iam-drift-01",
        "eventTime": "2026-11-15T13:00:00Z",
        "eventName": "PutRolePolicy",
        "eventSource": "iam.amazonaws.com",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "AIDA1234567890EXAMPLE",
            "arn": "arn:aws:iam::123456789012:user/compromised-operator",
        },
        "sourceIPAddress": "198.51.100.42",
        "requestParameters": {
            "roleName": "ProductionApplicationRole",
            "policyName": "BackdoorEscalationPolicy",
            "policyDocument": json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowFullAdmin",
                        "Effect": "Allow",
                        "Action": "*",
                        "Resource": "*",
                    }
                ],
            }),
        },
    }

    alerts = rule_engine.process_cloudtrail_event(drift_event)
    assert len(alerts) >= 1, "Mutating drift engine must detect PutRolePolicy wildcard escalation"

    drift_alert = next((a for a in alerts if str(a.get("cid")) == "50"), None)
    assert drift_alert is not None, "Alert must be mapped to CID 50"
    assert drift_alert["detection_mode"] == "CLOUDTRAIL_INLINE_DRIFT"
    assert drift_alert["service"] == "IAM"
    assert drift_alert["event_name"] == "PutRolePolicy"
    assert drift_alert["actor_arn"] == "arn:aws:iam::123456789012:user/compromised-operator"


# ── 5. S3 Bucket SSE & Public Access Block ───────────────────────────────────


def test_s3_bucket_encryption_and_public_access(rule_loader: RuleLoader):
    # Retrieve S3 rules
    s3_rules = rule_loader.get_rules_for_service("AWS", "S3", "aws_config_state")
    assert len(s3_rules) > 0, "S3 rules must be loaded"

    # Find rules for public access block and default encryption
    pab_rule = next((r for r in s3_rules if "public" in r.title.lower() or "block" in r.title.lower()), None)
    enc_rule = next((r for r in s3_rules if "encrypt" in r.title.lower() or "kms" in r.title.lower()), None)

    # Secure bucket
    secure_bucket = {
        "BucketName": "corporate-vault-secure",
        "ServerSideEncryptionConfiguration": {
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms",
                        "KMSMasterKeyId": "arn:aws:kms:us-east-1:123456789012:key/cmk-uuid",
                    }
                }
            ]
        },
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
        "PubliclyAccessible": False,
    }

    if pab_rule:
        assert evaluate_rule(secure_bucket, pab_rule) is False
    if enc_rule:
        assert evaluate_rule(secure_bucket, enc_rule) is False


# ── 6. CloudTrail Runtime Log Controls (CID 18 & 27–40) ──────────────────────


def test_cloudtrail_runtime_log_controls_cid_18_and_27_to_40(rule_engine: RuleEngine):
    # Event 1: Root user daily task / usage (CID 18 & CID 29)
    root_event = {
        "eventID": "evt-root-usage-01",
        "eventTime": "2026-11-15T13:10:00Z",
        "eventName": "DescribeInstances",
        "eventSource": "ec2.amazonaws.com",
        "eventType": "AwsApiCall",
        "userIdentity": {
            "type": "Root",
            "arn": "arn:aws:iam::123456789012:root",
        },
        "sourceIPAddress": "192.0.2.1",
    }
    alerts_root = rule_engine.process_cloudtrail_event(root_event)
    assert any(str(a.get("cid")) == "18" for a in alerts_root), "Root usage must fire CID 18"
    assert any(str(a.get("cid")) == "29" for a in alerts_root), "Root usage must fire CID 29"

    # Event 2: CloudTrail modification (StopLogging / DeleteTrail) (CID 31)
    stop_logging_event = {
        "eventID": "evt-stop-logging-01",
        "eventTime": "2026-11-15T13:11:00Z",
        "eventName": "StopLogging",
        "eventSource": "cloudtrail.amazonaws.com",
        "eventType": "AwsApiCall",
        "userIdentity": {"arn": "arn:aws:iam::123456789012:user/adversary"},
        "sourceIPAddress": "192.0.2.1",
        "requestParameters": {"name": "management-events-trail"},
    }
    alerts_cid31 = rule_engine.process_cloudtrail_event(stop_logging_event)
    assert any(str(a.get("cid")) == "31" for a in alerts_cid31), "StopLogging must fire CID 31"

    # Event 3: IAM policy changes (DeleteRolePolicy) (CID 30)
    iam_change_event = {
        "eventID": "evt-iam-delete-01",
        "eventTime": "2026-11-15T13:12:00Z",
        "eventName": "DeleteRolePolicy",
        "eventSource": "iam.amazonaws.com",
        "eventType": "AwsApiCall",
        "userIdentity": {"arn": "arn:aws:iam::123456789012:user/adversary"},
        "sourceIPAddress": "192.0.2.1",
        "requestParameters": {"roleName": "AppRole", "policyName": "OldPolicy"},
    }
    alerts_cid30 = rule_engine.process_cloudtrail_event(iam_change_event)
    assert any(str(a.get("cid")) == "30" for a in alerts_cid30), "DeleteRolePolicy must fire CID 30"

    # Event 4: S3 bucket policy changes (PutBucketPolicy) (CID 34)
    s3_change_event = {
        "eventID": "evt-s3-change-01",
        "eventTime": "2026-11-15T13:13:00Z",
        "eventName": "PutBucketPolicy",
        "eventSource": "s3.amazonaws.com",
        "eventType": "AwsApiCall",
        "userIdentity": {"arn": "arn:aws:iam::123456789012:user/adversary"},
        "sourceIPAddress": "192.0.2.1",
        "requestParameters": {"bucketName": "data-lake"},
    }
    alerts_cid34 = rule_engine.process_cloudtrail_event(s3_change_event)
    assert any(str(a.get("cid")) == "34" for a in alerts_cid34), "PutBucketPolicy must fire CID 34"


# ── 7. Deterministic Compliance Grader Policy & Mandate Rollup ───────────────


def test_deterministic_grader_policy_and_mandate_rollup(grader: DeterministicComplianceGrader):
    # Setup mixed estate: 1 secure SG, 1 insecure SG (fails CID 41), 1 secure role, 1 wildcard role (fails CID 50)
    resources = {
        "VPC": [
            {
                "urn": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-compliant",
                "GroupId": "sg-compliant",
                "IpPermissions": [{"FromPort": 22, "ToPort": 22, "IpProtocol": "tcp", "IpRanges": [{"CidrIp": "10.0.0.0/8"}]}],
            },
            {
                "urn": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-insecure",
                "GroupId": "sg-insecure",
                "IpPermissions": [{"FromPort": 22, "ToPort": 22, "IpProtocol": "tcp", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
            },
        ],
        "IAM": [
            {
                "urn": "arn:aws:iam::123456789012:role/SecureRole",
                "RoleName": "SecureRole",
                "PolicyDocument": {"Statement": [{"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "*"}]},
                "PolicyDocuments": [{"Statement": [{"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "*"}]}],
            },
            {
                "urn": "arn:aws:iam::123456789012:role/CompromisedRole",
                "RoleName": "CompromisedRole",
                "PolicyDocument": {"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]},
                "PolicyDocuments": [{"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}],
            },
        ],
    }

    t0 = time.perf_counter()
    result = grader.evaluate_all_without_ai(
        provider="AWS",
        resources_by_service=resources,
        cloudtrail_events=[],
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert result["grading_mode"] == "DETERMINISTIC_NON_AI"
    assert result["provider"] == "AWS"
    assert result["total_controls_evaluated"] == 700
    assert result["controls_failed"] >= 2
    assert elapsed_ms < 1000, f"Full 700-rule AWS evaluation took {elapsed_ms:.1f}ms (must be < 1000ms)"

    # Validate Policy Rollup
    policies = result["policies"]
    assert "CIS Amazon Web Services Foundations Benchmark" in policies
    cis_score = policies["CIS Amazon Web Services Foundations Benchmark"]
    assert cis_score["failed"] >= 2
    assert "41" in cis_score["failing_cids"]
    assert "50" in cis_score["failing_cids"]
    assert 0.0 <= cis_score["score_pct"] <= 100.0

    # Validate Mandate Rollup (SOC 2, PCI-DSS, HIPAA)
    mandates = result["mandates"]
    soc2_title = next((m for m in mandates.keys() if "SOC 2" in m), None)
    assert soc2_title is not None, "SOC 2 mandate must be present in rollups"
    soc2_score = mandates[soc2_title]
    assert "50" in soc2_score["failing_cids"]
    assert 0.0 <= soc2_score["score_pct"] <= 100.0


# ── 8. Multi-Cloud Catalog and Rule Coverage ─────────────────────────────────


def test_multi_cloud_catalog_and_rule_coverage(rule_loader: RuleLoader):
    # Rule distribution across the 4 canonical cloud providers
    aws_rules = [r for r in rule_loader.rules_by_id.values() if r.provider.upper() == "AWS"]
    azure_rules = [r for r in rule_loader.rules_by_id.values() if r.provider.upper() == "AZURE"]
    gcp_rules = [r for r in rule_loader.rules_by_id.values() if r.provider.upper() == "GCP"]
    oci_rules = [r for r in rule_loader.rules_by_id.values() if r.provider.upper() == "OCI"]

    assert len(aws_rules) == 700
    assert len(azure_rules) == 572
    assert len(gcp_rules) == 201
    assert len(oci_rules) == 92
    assert len(rule_loader.rules_by_id) == 1565
    assert len(rule_loader.rules_by_cid) == 1565

    # Policy and Mandate Registries
    policies = list_policies()
    mandates = list_mandates()
    assert len(policies) == 29
    assert len(mandates) == 38


# ── 9. Sub-Millisecond Rule Evaluation Performance Benchmark ─────────────────


def test_performance_sub_millisecond_eval(rule_loader: RuleLoader):
    rule = rule_loader.get_rule_by_cid("41")
    sample_sg = {
        "GroupId": "sg-perf-benchmark",
        "IpPermissions": [
            {
                "FromPort": 22,
                "ToPort": 22,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "192.168.1.0/24"}],
            }
        ],
    }

    # Execute 1,000 iterations to calculate average latency
    iterations = 1000
    t0 = time.perf_counter()
    for _ in range(iterations):
        evaluate_rule(sample_sg, rule)
    elapsed_total_ms = (time.perf_counter() - t0) * 1000
    avg_latency_ms = elapsed_total_ms / iterations

    assert avg_latency_ms < 0.1, f"Average per-rule evaluation was {avg_latency_ms:.4f}ms (must be < 0.1ms)"


# ── 10. End-to-End FastAPI Compliance Audit Pipeline ─────────────────────────


def test_end_to_end_fastapi_audit_pipeline(client: TestClient):
    # Simulate a full cloud audit request combining configuration snapshots + live CloudTrail stream
    audit_request = {
        "provider": "AWS",
        "account_id": "999888777666",
        "session_id": "audit-e2e-session-full",
        "resources_by_service": {
            "VPC": [
                {
                    "urn": "arn:aws:ec2:us-east-1:999888777666:security-group/sg-01",
                    "GroupId": "sg-01",
                    "IpPermissions": [
                        {
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpProtocol": "tcp",
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                }
            ],
            "IAM": [
                {
                    "urn": "arn:aws:iam::999888777666:role/DevRole",
                    "RoleName": "DevRole",
                    "PolicyDocument": {"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]},
                    "PolicyDocuments": [{"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}],
                }
            ],
        },
        "cloudtrail_events": [
            {
                "eventID": "evt-e2e-01",
                "eventTime": "2026-11-15T13:30:00Z",
                "eventName": "AuthorizeSecurityGroupIngress",
                "eventSource": "ec2.amazonaws.com",
                "userIdentity": {"arn": "arn:aws:iam::999888777666:user/admin"},
                "sourceIPAddress": "198.51.100.10",
                "requestParameters": {
                    "groupId": "sg-01",
                    "ipPermissions": {
                        "items": [
                            {
                                "fromPort": 22,
                                "toPort": 22,
                                "ipProtocol": "tcp",
                                "ipRanges": {"items": [{"cidrIp": "0.0.0.0/0"}]},
                            }
                        ]
                    },
                },
            }
        ],
    }

    response = client.post("/api/v1/cspm/evaluate/non-ai", json=audit_request)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["session_id"] == "audit-e2e-session-full"
    assert data["non_ai_guarantee"] is True
    assert data["provider"] == "AWS"

    # Execution summary assertions
    exec_summary = data["execution_summary"]
    assert exec_summary["total_controls_evaluated"] == 700
    assert exec_summary["controls_failed"] >= 2
    assert exec_summary["drift_alerts_detected"] >= 1
    assert exec_summary["latency_ms"] > 0

    # Warm request benchmark: second request executes from in-memory index in sub-second time
    resp_warm = client.post("/api/v1/cspm/evaluate/non-ai", json=audit_request)
    assert resp_warm.status_code == 200
    assert resp_warm.json()["execution_summary"]["latency_ms"] < 350, "Warm request must execute in < 350ms"

    # Failing evidence signals verification
    controls = data["controls"]
    assert controls["41"]["status"] == "FAIL"
    assert controls["50"]["status"] == "FAIL"

    # Drift alerts verification
    drift_alerts = data["drift_alerts"]
    assert any(str(d.get("cid")) == "41" for d in drift_alerts)

    # Catalog summary verification
    cat_resp = client.get("/api/v1/cspm/catalogs/summary")
    assert cat_resp.status_code == 200
    cat_data = cat_resp.json()
    assert cat_data["total_rules"] == 1565
    assert cat_data["policies_count"] == 29
    assert cat_data["mandates_count"] == 38
