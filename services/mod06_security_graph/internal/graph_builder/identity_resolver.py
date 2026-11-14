"""IAM Identity & Privilege Escalation Blast Radius Resolver (PRD-MOD-06)."""

from typing import Any, Dict, List, Optional, Set


ADMIN_POLICIES = {
    "arn:aws:iam::aws:policy/AdministratorAccess",
    "AdministratorAccess",
    "roles/owner",
    "roles/editor",
    "Contributor",
    "Owner",
}

PRIVESC_ACTIONS = {
    "iam:PassRole",
    "iam:CreatePolicyVersion",
    "iam:SetDefaultPolicyVersion",
    "iam:AttachUserPolicy",
    "iam:AttachGroupPolicy",
    "iam:AttachRolePolicy",
    "iam:PutUserPolicy",
    "iam:PutGroupPolicy",
    "iam:PutRolePolicy",
    "iam:AddUserToGroup",
    "iam:UpdateAssumeRolePolicy",
}


class IdentityBlastResolver:
    """Calculates identity blast radius score I_blast and identifies privilege escalation."""

    @staticmethod
    def resolve_blast_radius(
        attached_policies: Optional[List[str]] = None,
        policy_actions: Optional[List[str]] = None,
        is_root: bool = False,
    ) -> Dict[str, Any]:
        """Calculates identity blast radius classification and I_blast score."""
        if is_root:
            return {
                "blast_tier": "ADMIN",
                "i_blast": 100.0,
                "is_admin": True,
                "privesc_risk": False,
                "reason": "Root / Super Admin account",
            }

        policies = set(attached_policies or [])
        actions = set(policy_actions or [])

        # Check for full admin access
        has_admin_policy = any(p in ADMIN_POLICIES or "AdministratorAccess" in p for p in policies)
        has_wildcard = "*:*" in actions or ("*" in actions and not policies)

        if has_admin_policy or has_wildcard:
            return {
                "blast_tier": "ADMIN",
                "i_blast": 100.0,
                "is_admin": True,
                "privesc_risk": True,
                "reason": "Unrestricted administrative privileges (AdministratorAccess / *:* )",
            }

        # Check for IAM privilege escalation paths
        has_privesc = bool(actions.intersection(PRIVESC_ACTIONS))
        if has_privesc:
            return {
                "blast_tier": "ADMIN",
                "i_blast": 100.0,
                "is_admin": True,
                "privesc_risk": True,
                "reason": "IAM actions present enabling privilege escalation to Administrator",
            }

        # Broad Read/Write access (e.g. s3:*, dynamodb:*)
        has_broad_rw = any(
            a.endswith(":*") for a in actions if not a.startswith("kms:") and not a.startswith("cloudwatch:")
        )
        if has_broad_rw or len(actions) > 20:
            return {
                "blast_tier": "BROAD_RW",
                "i_blast": 60.0,
                "is_admin": False,
                "privesc_risk": False,
                "reason": "Broad Read/Write access across cloud services",
            }

        # Scoped access
        if actions or policies:
            return {
                "blast_tier": "SCOPED",
                "i_blast": 20.0,
                "is_admin": False,
                "privesc_risk": False,
                "reason": "Scoped least-privilege role/policy",
            }

        return {
            "blast_tier": "NONE",
            "i_blast": 0.0,
            "is_admin": False,
            "privesc_risk": False,
            "reason": "No attached IAM policies or permissions",
        }

