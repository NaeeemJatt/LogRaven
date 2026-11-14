"""IAM Policy AST Generator (FR-MOD7-01, TC-MOD7-001).

Parses cloud IAM policy JSON documents (AWS IAM, GCP IAM, Azure RBAC) into
structured Abstract Syntax Tree (AST) representations with Action normalization.
"""

from dataclasses import dataclass, field
import fnmatch
from typing import Any, Dict, List, Optional, Set


@dataclass
class PolicyStatementAST:
    sid: Optional[str] = None
    effect: str = "Allow"  # Allow | Deny
    actions: List[str] = field(default_factory=list)
    not_actions: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyAST:
    policy_name: str
    version: str = "2012-10-17"
    statements: List[PolicyStatementAST] = field(default_factory=list)


class PolicyASTParser:
    """Parses raw cloud IAM policy dictionaries into normalized PolicyAST objects."""

    @classmethod
    def parse_aws_policy(cls, policy_doc: Dict[str, Any], policy_name: str = "unnamed") -> PolicyAST:
        """Parses standard AWS IAM policy document into PolicyAST."""
        statements = []
        raw_stmts = policy_doc.get("Statement", [])
        if isinstance(raw_stmts, dict):
            raw_stmts = [raw_stmts]

        for stmt in raw_stmts:
            effect = stmt.get("Effect", "Allow")

            # Actions
            actions_raw = stmt.get("Action", [])
            if isinstance(actions_raw, str):
                actions = [actions_raw]
            else:
                actions = list(actions_raw)

            not_actions_raw = stmt.get("NotAction", [])
            if isinstance(not_actions_raw, str):
                not_actions = [not_actions_raw]
            else:
                not_actions = list(not_actions_raw)

            # Resources
            res_raw = stmt.get("Resource", ["*"])
            if isinstance(res_raw, str):
                resources = [res_raw]
            else:
                resources = list(res_raw)

            conditions = stmt.get("Condition", {})

            statements.append(
                PolicyStatementAST(
                    sid=stmt.get("Sid"),
                    effect=effect,
                    actions=actions,
                    not_actions=not_actions,
                    resources=resources,
                    conditions=conditions,
                )
            )

        return PolicyAST(
            policy_name=policy_name,
            version=policy_doc.get("Version", "2012-10-17"),
            statements=statements,
        )

    @staticmethod
    def matches_action(pattern: str, action: str) -> bool:
        """Checks if an IAM action matches a wildcard pattern (e.g. 's3:*' matches 's3:GetObject')."""
        return fnmatch.fnmatchcase(action.lower(), pattern.lower())

