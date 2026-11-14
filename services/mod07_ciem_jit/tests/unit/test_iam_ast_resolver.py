"""Unit tests for Five-Layer IAM AST Resolver (TC-MOD7-001, FR-MOD7-01)."""

import pytest
from services.mod07_ciem_jit.internal.ast_resolver.scp_boundary_filter import EffectivePermissionResolver


def test_tc_mod7_001_scp_deny_overrides_admin_identity_policy():
    """TC-MOD7-001: Feed IAM Role with AdministratorAccess identity policy and an SCP with Deny on s3:*.
    
    Expected Pass Criteria:
    Evaluator resolves effective permissions without s3:*; validates SCP overrides identity policy.
    """
    # 1. Identity policy: AdministratorAccess (Allow *)
    identity_policies = [
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "FullAdministratorAccess",
                    "Effect": "Allow",
                    "Action": "*",
                    "Resource": "*",
                }
            ],
        }
    ]

    # 2. Service Control Policy (SCP) at AWS Organization level: Deny all s3 operations
    scp_policies = [
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "DenyS3AcrossAccount",
                    "Effect": "Deny",
                    "Action": "s3:*",
                    "Resource": "*",
                }
            ],
        }
    ]

    resolution = EffectivePermissionResolver.resolve_effective_permissions(
        identity_policies=identity_policies,
        scp_policies=scp_policies,
    )

    effective_actions = resolution["effective_actions"]

    # Assertion 1: S3 actions are completely absent from effective permissions
    assert len(effective_actions) > 0, "Effective actions should contain non-S3 permissions"
    s3_actions = [a for a in effective_actions if a.lower().startswith("s3:")]
    assert len(s3_actions) == 0, f"SCP failed to block S3 actions! Found: {s3_actions}"

    # Assertion 2: Other actions (EC2, IAM, Lambda, etc.) are allowed
    assert "ec2:RunInstances" in effective_actions or any("ec2:" in a.lower() for a in effective_actions)

    # Assertion 3: SCP override flag is True and Deny action was tracked
    assert resolution["scp_override_applied"] is True
    assert "s3:*" in resolution["explicit_denies_applied"]
    assert resolution["is_admin"] is False, "Role with explicit Deny on S3 is not unrestricted Administrator"


def test_permission_boundary_acts_as_ceiling():
    """Verifies that Permission Boundaries intersect with identity policy."""
    identity_policies = [
        {
            "Statement": [
                {"Effect": "Allow", "Action": ["ec2:*", "s3:*"], "Resource": "*"}
            ]
        }
    ]

    # Boundary allows only s3:GetObject and s3:ListBucket
    boundaries = [
        {
            "Statement": [
                {"Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"], "Resource": "*"}
            ]
        }
    ]

    resolution = EffectivePermissionResolver.resolve_effective_permissions(
        identity_policies=identity_policies,
        permission_boundaries=boundaries,
    )

    effective = resolution["effective_actions"]
    # Only S3 Get and List should survive the boundary intersection
    assert "s3:GetObject" in effective
    assert "s3:ListBucket" in effective
    assert not any("ec2:" in a.lower() for a in effective)
