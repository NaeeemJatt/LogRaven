"""Slack & Teams ChatOps JIT Approval Workflows (FR-MOD7-04, TC-MOD7-004).

Builds interactive Slack Block Kit messages for requesting, approving, and rejecting
ephemeral Just-In-Time cloud access leases.
"""

from typing import Any, Dict, List, Optional
import uuid


class SlackJITHandler:
    """Formats and processes Slack Block Kit payloads for JIT access requests."""

    @classmethod
    def create_request_blocks(
        cls,
        lease_id: uuid.UUID,
        requester_email: str,
        target_role_arn: str,
        duration_minutes: int,
        justification: str,
    ) -> Dict[str, Any]:
        """Constructs Slack Block Kit interactive message."""
        return {
            "text": f"JIT Access Request from {requester_email}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🔐 LogRaven JIT Access Request",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Requester:*\n{requester_email}"},
                        {"type": "mrkdwn", "text": f"*Duration:*\n{duration_minutes} minutes"},
                        {"type": "mrkdwn", "text": f"*Target Role:*\n`{target_role_arn}`"},
                        {"type": "mrkdwn", "text": f"*Lease ID:*\n`{lease_id}`"},
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Business Justification:*\n_{justification}_",
                    },
                },
                {
                    "type": "actions",
                    "block_id": f"jit_actions_{lease_id}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve Access"},
                            "style": "primary",
                            "action_id": "approve_jit_lease",
                            "value": str(lease_id),
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Reject"},
                            "style": "danger",
                            "action_id": "reject_jit_lease",
                            "value": str(lease_id),
                        },
                    ],
                },
            ],
        }

    @classmethod
    def create_approval_confirmation(
        cls,
        lease_id: uuid.UUID,
        approver_email: str,
        target_role_arn: str,
        expires_at_iso: str,
    ) -> Dict[str, Any]:
        """Confirmation message posted after approval."""
        return {
            "text": f"✅ JIT Access Approved by {approver_email}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"✅ *JIT Lease Approved and Activated*\n"
                            f"• *Approver:* {approver_email}\n"
                            f"• *Target Role:* `{target_role_arn}`\n"
                            f"• *Expires At:* `{expires_at_iso}`\n"
                            f"• *Status:* `ACTIVE`"
                        ),
                    },
                }
            ],
        }

