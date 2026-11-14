"""IAM Set-Theoretic Evaluator (FR-MOD7-01).

Calculates Allow sets and Deny sets, enforcing the foundational cloud principle:
Explicit Deny strictly overrides any Allow.
"""

import fnmatch
from typing import Any, Dict, List, Optional, Set

from services.mod07_ciem_jit.internal.ast_resolver.policy_ast import PolicyAST, PolicyStatementAST

# Standard representative catalog of AWS service actions for wildcard expansion
COMMON_AWS_ACTIONS = {
    # EC2
    "ec2:RunInstances", "ec2:DescribeInstances", "ec2:StopInstances", "ec2:TerminateInstances",
    "ec2:CreateSecurityGroup", "ec2:AuthorizeSecurityGroupIngress", "ec2:DescribeSecurityGroups",
    # S3
    "s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject", "s3:PutBucketPolicy",
    "s3:GetBucketAcl", "s3:PutBucketAcl", "s3:CreateBucket", "s3:DeleteBucket",
    # IAM
    "iam:PassRole", "iam:CreateRole", "iam:AttachRolePolicy", "iam:PutRolePolicy",
    "iam:CreateUser", "iam:CreateAccessKey", "iam:ListUsers", "iam:GetUser",
    "iam:AttachUserPolicy", "iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion",
    # Lambda
    "lambda:CreateFunction", "lambda:InvokeFunction", "lambda:UpdateFunctionCode",
    "lambda:AddPermission", "lambda:ListFunctions",
    # DynamoDB
    "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan",
    # KMS
    "kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey",
}


class SetEvaluator:
    """Computes set intersections, differences, and wildcard matching for cloud actions."""

    @classmethod
    def expand_actions(cls, action_patterns: List[str], known_catalog: Optional[Set[str]] = None) -> Set[str]:
        """Expands wildcard patterns (e.g. 's3:*', '*') into explicit action sets."""
        catalog = known_catalog or COMMON_AWS_ACTIONS
        matched: Set[str] = set()

        for pattern in action_patterns:
            if pattern in ("*", "*:*"):
                return set(catalog).union({"*:*"})

            pattern_lower = pattern.lower()
            matching = {act for act in catalog if fnmatch.fnmatchcase(act.lower(), pattern_lower)}
            if matching:
                matched.update(matching)
            else:
                # Retain literal pattern if not in standard catalog
                matched.add(pattern)

        return matched

    @classmethod
    def evaluate_policy_statements(
        cls,
        statements: List[PolicyStatementAST],
        action_catalog: Optional[Set[str]] = None,
    ) -> Set[str]:
        """Calculates effective allowed actions from a list of statements: (Allows - Denies)."""
        allow_patterns: List[str] = []
        deny_patterns: List[str] = []

        for stmt in statements:
            if stmt.effect.lower() == "allow":
                allow_patterns.extend(stmt.actions)
            elif stmt.effect.lower() == "deny":
                deny_patterns.extend(stmt.actions)

        allowed_set = cls.expand_actions(allow_patterns, action_catalog)
        denied_set = cls.expand_actions(deny_patterns, action_catalog)

        # Explicit Deny strictly overrides any Allow
        # In addition, check if wildcard deny matches (e.g. deny 's3:*')
        effective_allowed: Set[str] = set()
        for action in allowed_set:
            if action in denied_set:
                continue
            is_denied = any(fnmatch.fnmatchcase(action.lower(), dp.lower()) for dp in deny_patterns)
            if not is_denied:
                effective_allowed.add(action)

        return effective_allowed

