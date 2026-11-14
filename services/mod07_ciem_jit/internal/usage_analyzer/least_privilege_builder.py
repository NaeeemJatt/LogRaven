"""Least-Privilege IAM Policy Builder (FR-MOD7-03, TC-MOD7-003).

Generates hardened, minimal replacement IAM policies containing only actions
actually invoked within the 90-day observation window.
"""

import json
from typing import Any, Dict, List, Optional


class LeastPrivilegeBuilder:
    """Emits production-ready, pruned IAM policy documents."""

    @classmethod
    def build_replacement_policy(
        cls,
        used_actions: List[str],
        policy_name: str = "PrunedLeastPrivilegePolicy",
        resource_arn: str = "*",
    ) -> Dict[str, Any]:
        """Emits hardened IAM policy JSON containing exactly the used actions (TC-MOD7-003)."""
        sorted_actions = sorted(list(set(used_actions)))

        statement = {
            "Sid": "LogRavenLeastPrivilegeRightSized",
            "Effect": "Allow",
            "Action": sorted_actions,
            "Resource": resource_arn,
        }

        policy_doc = {
            "Version": "2012-10-17",
            "Statement": [statement],
        }

        return {
            "policy_name": policy_name,
            "actions_count": len(sorted_actions),
            "policy_document": policy_doc,
            "policy_json": json.dumps(policy_doc, indent=2),
        }

