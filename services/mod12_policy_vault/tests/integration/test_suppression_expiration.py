"""Integration tests for Suppression Rule Expiration Sweeper (TC-MOD12-003).

Verifies that rules reaching expiration date transition to EXPIRED, re-opening findings.
"""

from datetime import datetime, timedelta, timezone
import pytest

from services.mod12_policy_vault.internal.suppression_engine.boolean_evaluator import (
    BooleanSuppressionEvaluator,
    FindingContext,
    SuppressionRuleData,
)
from services.mod12_policy_vault.internal.suppression_engine.expiration_sweeper import SuppressionExpirationSweeper


def test_tc_mod12_003_suppression_expiration_and_reopen():
    """TC-MOD12-003: Active suppression rule reaches expiration date.

    Expected: Midnight sweeper transitions status to EXPIRED; subsequent audits re-open findings on affected assets.
    """
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(hours=1)

    # 1. Rule that has expired
    rule = SuppressionRuleData(
        rule_id="waiver-rule-001",
        name="Temporary S3 waiver",
        status="ACTIVE",
        finding_type="IOM-S3-PUBLIC-ACL",
        account_ids=["112233445566"],
        regions=["us-east-1"],
        expires_at=expired_time,
        justification="Expired waiver",
    )

    finding = FindingContext(
        finding_type="IOM-S3-PUBLIC-ACL",
        account_id="112233445566",
        region="us-east-1",
    )

    # 2. Run expiration sweeper
    expired_count, updated_rules = SuppressionExpirationSweeper.sweep_rules(
        rules=[rule],
        current_time=now,
    )

    assert expired_count == 1
    assert rule.status == "EXPIRED"

    # 3. Subsequent audit evaluation on affected asset
    is_suppressed, matched_rule = BooleanSuppressionEvaluator.is_finding_suppressed(
        finding=finding,
        rules=updated_rules,
        current_time=now,
    )

    # Finding is NO LONGER suppressed -> re-opened for audit remediation!
    assert is_suppressed is False
    assert matched_rule is None

