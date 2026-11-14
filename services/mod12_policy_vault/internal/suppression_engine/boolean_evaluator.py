"""CrowdStrike Dual-Engine Boolean Suppression Algorithm (PRD-MOD-12 / TC-MOD12-002).

Evaluates finding context against scoped suppression rules honoring:
finding_type, account_ids, regions, tag_filters, and expiration timestamps.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class FindingContext:
    """Normalized finding representation for suppression evaluation."""

    def __init__(
        self,
        finding_type: str,
        account_id: str,
        region: str,
        tags: Optional[Dict[str, str]] = None,
        asset_urn: Optional[str] = None,
    ):
        self.finding_type = finding_type
        self.account_id = account_id
        self.region = region
        self.tags = tags or {}
        self.asset_urn = asset_urn


class SuppressionRuleData:
    """Normalized suppression rule configuration."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        status: str = "ACTIVE",
        finding_type: Optional[str] = None,
        account_ids: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        tag_filters: Optional[Dict[str, str]] = None,
        expires_at: Optional[datetime] = None,
        justification: str = "",
    ):
        self.rule_id = rule_id
        self.name = name
        self.status = status
        self.finding_type = finding_type
        self.account_ids = account_ids or []
        self.regions = regions or []
        self.tag_filters = tag_filters or {}
        self.expires_at = expires_at
        self.justification = justification


class BooleanSuppressionEvaluator:
    """Exact Boolean evaluation algorithm reverse-engineered from CrowdStrike Falcon Cloud Security."""

    @classmethod
    def is_finding_suppressed(
        cls,
        finding: FindingContext,
        rules: List[SuppressionRuleData],
        current_time: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[SuppressionRuleData]]:
        """Evaluates whether a finding is suppressed by any active rule."""
        now = current_time or datetime.now(timezone.utc)

        for rule in rules:
            # 1. Rule must be in ACTIVE status
            if rule.status != "ACTIVE":
                continue

            # 2. Rule must not be expired
            if rule.expires_at and now > rule.expires_at:
                continue

            # 3. Finding type check
            if rule.finding_type and rule.finding_type != finding.finding_type:
                continue

            # 4. Account ID check (if rule specifies accounts, finding's account must be in list)
            if rule.account_ids and finding.account_id not in rule.account_ids:
                continue

            # 5. Region check (if rule specifies regions, finding's region must be in list)
            if rule.regions and finding.region not in rule.regions:
                continue

            # 6. Tag filters (All tags defined in rule must match on finding)
            if rule.tag_filters:
                if not all(finding.tags.get(k) == v for k, v in rule.tag_filters.items()):
                    continue

            # All scoped conditions matched and rule is active
            return True, rule

        return False, None
