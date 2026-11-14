"""Suppression Rule Expiration Sweeper (PRD-MOD-12 / TC-MOD12-003).

Runs periodically (e.g. daily at midnight UTC) to transition expired suppression rules
to 'EXPIRED' status, ensuring findings are re-evaluated and re-opened.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from services.mod12_policy_vault.internal.suppression_engine.boolean_evaluator import SuppressionRuleData


class SuppressionExpirationSweeper:
    """Detects and transitions expired suppression rules."""

    @classmethod
    def sweep_rules(
        cls,
        rules: List[SuppressionRuleData],
        current_time: Optional[datetime] = None,
    ) -> Tuple[int, List[SuppressionRuleData]]:
        """Sweeps in-memory rules, transitions expired ones to EXPIRED, and returns count of expired rules."""
        now = current_time or datetime.now(timezone.utc)
        expired_count = 0

        for rule in rules:
            if rule.status == "ACTIVE" and rule.expires_at and now > rule.expires_at:
                rule.status = "EXPIRED"
                expired_count += 1

        return expired_count, rules
