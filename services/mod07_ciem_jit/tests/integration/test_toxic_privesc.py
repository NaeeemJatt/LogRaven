"""Integration tests for Toxic Privilege Escalation and 90-Day Right-Sizing (TC-MOD7-002, TC-MOD7-003)."""

import json
import pytest

from services.mod07_ciem_jit.internal.toxic_matrix.combination_checker import ToxicCombinationChecker
from services.mod07_ciem_jit.internal.usage_analyzer.least_privilege_builder import LeastPrivilegeBuilder
from services.mod07_ciem_jit.internal.usage_analyzer.usage_diff import UsageDiffAnalyzer


def test_tc_mod7_002_privesc_passrole_ec2_runinstances():
    """TC-MOD7-002: Role has iam:PassRole and ec2:RunInstances.
    
    Expected Pass Criteria:
    Toxic matrix flags AWS-PRIVESC-002 (Critical, Ability to launch EC2 instance with administrative role).
    """
    granted_actions = [
        "ec2:DescribeInstances",
        "ec2:RunInstances",
        "iam:PassRole",
        "s3:GetObject",
    ]

    result = ToxicCombinationChecker.evaluate_principal_actions(
        granted_actions=granted_actions,
        provider="aws",
    )

    assert result["has_toxic_combinations"] is True
    assert "AWS-PRIVESC-002" in result["vector_ids"]

    # Locate and verify the vector details
    matched_vector = next(v for v in result["toxic_vectors"] if v["vector_id"] == "AWS-PRIVESC-002")
    assert matched_vector["severity"] == "CRITICAL"
    assert "Launch EC2 Instance" in matched_vector["title"]
    assert "iam:PassRole" in matched_vector["required_actions"]
    assert "ec2:RunInstances" in matched_vector["required_actions"]


def test_tc_mod7_003_90day_usage_least_privilege_pruning():
    """TC-MOD7-003: Principal granted 150 EC2/S3 actions; CloudTrail proves only 4 actions were called over 90 days.
    
    Expected Pass Criteria:
    least_privilege_builder emits clean JSON policy containing exactly those 4 actions + required resource wildcards.
    """
    # 150 simulated granted actions across EC2, S3, RDS, DynamoDB
    granted_actions = [f"ec2:Action{i}" for i in range(75)] + [f"s3:Action{i}" for i in range(75)]
    assert len(granted_actions) == 150

    # Real-world usage proves only 4 actions were invoked in 90 days:
    used_actions_90d = [
        "s3:GetObject",
        "s3:ListBucket",
        "ec2:DescribeInstances",
        "ec2:StopInstances",
    ]

    # 1. Analyze usage diff
    diff = UsageDiffAnalyzer.calculate_diff(
        granted_actions=granted_actions,
        used_actions_90d=used_actions_90d,
    )

    assert diff["total_granted_count"] == 150
    assert diff["used_actions_count"] == 4
    assert diff["unused_actions_count"] == 150  # 4 were not part of the synthetic set, or if included:
    assert diff["is_overprivileged"] is True

    # 2. Build least-privilege replacement policy
    policy_output = LeastPrivilegeBuilder.build_replacement_policy(
        used_actions=used_actions_90d,
        policy_name="CustomerWorkloadPrunedPolicy",
        resource_arn="*",
    )

    assert policy_output["actions_count"] == 4
    policy_doc = policy_output["policy_document"]

    # Assert clean policy structure
    assert policy_doc["Version"] == "2012-10-17"
    statement = policy_doc["Statement"][0]
    assert statement["Effect"] == "Allow"
    assert statement["Resource"] == "*"
    assert sorted(statement["Action"]) == sorted(used_actions_90d)

    # Valid JSON serialization
    serialized = json.loads(policy_output["policy_json"])
    assert serialized == policy_doc

