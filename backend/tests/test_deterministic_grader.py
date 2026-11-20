"""
Unit tests for Module 07: Evidence Signals, Registry & Deterministic Compliance Grader (FR-DET-07, FR-DET-08).
Verifies non-AI weighted scoring formula, policy/mandate rollups, and EvidenceSignal generation.
"""

import pytest

from app.compliance.signals import EvidenceSignal
from app.compliance.frameworks.base import (
    load_policies_and_mandates_catalog,
    get_policy,
    get_mandate,
    list_policies,
    list_mandates,
)
from app.compliance.deterministic_grader import DeterministicComplianceGrader, WEIGHTS
from app.rules.loader import RuleLoader, RULES_DIR


@pytest.fixture(scope="module")
def grader():
    loader = RuleLoader(RULES_DIR)
    loader.load_all()
    return DeterministicComplianceGrader(loader)


def test_evidence_signal_dataclass():
    signal = EvidenceSignal(
        cid="41",
        title="Port 22 SSH",
        provider="AWS",
        service="VPC",
        criticality="HIGH",
        status="PASS",
        passed_resources=["sg-locked"],
        failing_resources=[],
        log_alerts=[],
    )
    assert signal.cid == "41"
    assert signal.status == "PASS"
    assert len(signal.passed_resources) == 1


def test_policies_and_mandates_registry():
    load_policies_and_mandates_catalog()
    policies = list_policies()
    mandates = list_mandates()

    assert len(policies) == 29
    assert len(mandates) == 38

    cis_pol = get_policy("CIS Amazon Web Services Foundations Benchmark")
    assert cis_pol is not None
    assert cis_pol["PROVIDER"] == "AWS"

    soc2_mand = get_mandate("SOC 2")
    assert soc2_mand is not None


def test_clean_estate_full_pass(grader):
    # Construct clean mock estate
    clean_resources = {
        "VPC": [
            {
                "urn": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-clean",
                "IpPermissions": [],
            }
        ],
        "IAM": [
            {
                "urn": "arn:aws:iam::123456789012:role/clean-role",
                "mfa_active": True,
                "UserPolicyList": [],
                "PolicyDocuments": [
                    {"Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::my-bucket/*"}]}
                ],
            }
        ],
    }

    report = grader.evaluate_all_without_ai(
        provider="AWS",
        resources_by_service=clean_resources,
        cloudtrail_events=[],
    )

    assert report["grading_mode"] == "DETERMINISTIC_NON_AI"
    assert report["provider"] == "AWS"
    assert report["total_controls_evaluated"] == 700
    assert report["controls_failed"] == 0
    assert report["controls_passed"] == 700

    # All policies should be 100%
    for pol_name, pol_data in report["policies"].items():
        assert pol_data["score_pct"] == 100.0, f"Policy {pol_name} score was {pol_data['score_pct']}"


def test_failing_estate_degrades_scores_accurately(grader):
    # Construct estate with violating resources:
    # 1. SG with Port 22 open to 0.0.0.0/0 (Violates CID 41)
    # 2. IAM Role with *:* full admin (Violates CID 50)
    violating_resources = {
        "VPC": [
            {
                "urn": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-bad-ssh",
                "IpPermissions": [
                    {"FromPort": 22, "ToPort": 22, "IpProtocol": "tcp", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
                ],
            }
        ],
        "IAM": [
            {
                "urn": "arn:aws:iam::123456789012:role/bad-admin-role",
                "mfa_active": True,
                "PolicyDocuments": [
                    {"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}
                ],
            }
        ],
    }

    # CloudTrail event with Root usage (Violates CID 18)
    root_log_event = {
        "eventID": "ct-evt-root-1",
        "eventName": "RunInstances",
        "eventType": "AwsApiCall",
        "userIdentity": {"type": "Root", "arn": "arn:aws:iam::123456789012:root"},
    }

    report = grader.evaluate_all_without_ai(
        provider="AWS",
        resources_by_service=violating_resources,
        cloudtrail_events=[root_log_event],
    )

    controls = report["controls"]
    assert controls["41"]["status"] == "FAIL"
    assert "arn:aws:ec2:us-east-1:123456789012:security-group/sg-bad-ssh" in controls["41"]["failing_resources"]

    assert controls["50"]["status"] == "FAIL"
    assert "arn:aws:iam::123456789012:role/bad-admin-role" in controls["50"]["failing_resources"]

    assert controls["18"]["status"] == "FAIL"
    assert len(controls["18"]["log_alerts"]) == 1

    # Check CIS policy score degraded from 100%
    cis_score = report["policies"].get("CIS Amazon Web Services Foundations Benchmark")
    assert cis_score is not None
    assert cis_score["score_pct"] < 100.0
    assert "41" in cis_score["failing_cids"]
