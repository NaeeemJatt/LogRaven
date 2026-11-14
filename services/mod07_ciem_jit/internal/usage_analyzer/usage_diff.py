"""90-Day Usage Diff Analyzer (FR-MOD7-03, TC-MOD7-003).

Diffs granted cloud actions against real-world CloudTrail & IAM Access Analyzer
historical usage over a 90-day window to identify dormant permissions.
"""

from typing import Any, Dict, List, Set


class UsageDiffAnalyzer:
    """Analyzes discrepancy between granted entitlements and actual cloud activity."""

    @classmethod
    def calculate_diff(
        cls,
        granted_actions: List[str],
        used_actions_90d: List[str],
    ) -> Dict[str, Any]:
        """Calculates dormant permissions and over-privilege metrics."""
        granted_set = set(granted_actions)
        used_set = set(used_actions_90d)

        # Unused actions = granted minus used
        unused_set = granted_set - used_set
        unused_count = len(unused_set)
        total_granted = len(granted_set)

        unused_pct = (unused_count / total_granted * 100.0) if total_granted > 0 else 0.0

        return {
            "total_granted_count": total_granted,
            "used_actions_count": len(used_set),
            "unused_actions_count": unused_count,
            "unused_percentage": round(unused_pct, 2),
            "used_actions": sorted(list(used_set)),
            "unused_actions": sorted(list(unused_set)),
            "is_overprivileged": unused_pct >= 50.0 or unused_count >= 10,
        }
