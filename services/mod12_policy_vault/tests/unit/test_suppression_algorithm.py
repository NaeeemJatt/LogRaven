"""Unit tests for CrowdStrike Dual-Engine Boolean Suppression Algorithm (TC-MOD12-002).

Verifies exact Boolean evaluation of scoped suppressions (region, account, tags, finding type).
"""

from datetime import datetime, timedelta, timezone
import pytest

from services.mod12_policy_vault.internal.suppression_engine.boolean_evaluator import (
    BooleanSuppressionEvaluator,
    FindingContext,
    SuppressionRuleData,
)


def test_tc_mod12_002_region_mismatch_not_suppressed():
    """TC-MOD12-002: Finding in us-west-2 evaluated against suppression rule scoped strictly to us-east-1.

    Expected: Algorithm evaluates to is_suppressed = false (region mismatch).
    """
    # 1. Suppression rule scoped strictly to us-east-1
    rule = SuppressionRuleData(
        rule_id="suppress-east-rule",
        name="Temporary S3 public access waiver",
        status="ACTIVE",
        finding_type="IOM-S3-PUBLIC-ACL",
        account_ids=["123456789012"],
        regions=["us-east-1"],
        tag_filters={"Environment": "Development"},
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        justification="Approved dev migration waiver",
    )

    # 2. Finding originating in us-west-2 (mismatch!)
    finding = FindingContext(
        finding_type="IOM-S3-PUBLIC-ACL",
        account_id="123456789012",
        region="us-west-2",
        tags={"Environment": "Development"},
    )

    # 3. Evaluate suppression
    is_suppressed, matched_rule = BooleanSuppressionEvaluator.is_finding_suppressed(
        finding=finding,
        rules=[rule],
    )

    assert is_suppressed is False
    assert matched_rule is None


def test_matching_finding_is_suppressed():
    """Verifies that a finding matching all scoped criteria evaluates to is_suppressed = true."""
    rule = SuppressionRuleData(
        rule_id="suppress-east-rule",
        name="Temporary S3 public access waiver",
        status="ACTIVE",
        finding_type="IOM-S3-PUBLIC-ACL",
        account_ids=["123456789012"],
        regions=["us-east-1"],
        tag_filters={"Environment": "Development"},
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    finding = FindingContext(
        finding_type="IOM-S3-PUBLIC-ACL",
        account_id="123456789012",
        region="us-east-1",
        tags={"Environment": "Development", "Team": "DevOps"},
    )

    is_suppressed, matched_rule = BooleanSuppressionEvaluator.is_finding_suppressed(
        finding=finding,
        rules=[rule],
    )

    assert is_suppressed is True
    assert matched_rule is not None
    assert matched_rule.rule_id == "suppress-east-rule"

