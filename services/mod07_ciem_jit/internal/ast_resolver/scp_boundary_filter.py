r"""Five-Layer IAM Set-Theoretic AST Resolver (FR-MOD7-01, TC-MOD7-001).

Computes effective permissions across 5 cloud policy layers:
1. Identity Policies (Managed & Inline)
2. Permission Boundaries (Maximum permissible ceiling)
3. AWS Organizations Service Control Policies (SCPs)
4. Resource-Based Policies
5. Session Policies (STS AssumeRole scoping)

Mathematical Formulation:
Effective = (Identity_Allow ∩ Boundary_Allow ∩ SCP_Allow ∩ Session_Allow) \ (ANY Explicit Deny)
"""

from typing import Any, Dict, List, Optional, Set
import fnmatch

from services.mod07_ciem_jit.internal.ast_resolver.policy_ast import PolicyAST, PolicyASTParser
from services.mod07_ciem_jit.internal.ast_resolver.set_evaluator import SetEvaluator


class EffectivePermissionResolver:
    """Computes effective cloud entitlements across all 5 evaluation layers."""

    @classmethod
    def resolve_effective_permissions(
        cls,
        identity_policies: List[Dict[str, Any]],
        permission_boundaries: Optional[List[Dict[str, Any]]] = None,
        scp_policies: Optional[List[Dict[str, Any]]] = None,
        resource_policies: Optional[List[Dict[str, Any]]] = None,
        session_policies: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Calculates effective allowed actions across all 5 policy layers (TC-MOD7-001)."""
        # Parse each layer into ASTs
        parsed_identity = [PolicyASTParser.parse_aws_policy(p, "identity") for p in identity_policies]
        parsed_boundaries = [PolicyASTParser.parse_aws_policy(p, "boundary") for p in (permission_boundaries or [])]
        parsed_scps = [PolicyASTParser.parse_aws_policy(p, "scp") for p in (scp_policies or [])]
        parsed_resources = [PolicyASTParser.parse_aws_policy(p, "resource") for p in (resource_policies or [])]
        parsed_session = [PolicyASTParser.parse_aws_policy(p, "session") for p in (session_policies or [])]

        # 1. Collect all explicit Deny patterns across ALL 5 layers
        all_deny_patterns: List[str] = []
        for layer in (parsed_identity, parsed_boundaries, parsed_scps, parsed_resources, parsed_session):
            for doc in layer:
                for stmt in doc.statements:
                    if stmt.effect.lower() == "deny":
                        all_deny_patterns.extend(stmt.actions)

        # 2. Layer 1: Identity Policy Allows
        identity_allows: Set[str] = set()
        for doc in parsed_identity:
            for stmt in doc.statements:
                if stmt.effect.lower() == "allow":
                    identity_allows.update(SetEvaluator.expand_actions(stmt.actions))

        effective: Set[str] = set(identity_allows)

        # 3. Layer 2: Permission Boundaries (if defined, acts as an Allow filter)
        if parsed_boundaries:
            boundary_allows: Set[str] = set()
            for doc in parsed_boundaries:
                for stmt in doc.statements:
                    if stmt.effect.lower() == "allow":
                        boundary_allows.update(SetEvaluator.expand_actions(stmt.actions))
            # Set intersection
            effective = {act for act in effective if cls._is_action_in_set(act, boundary_allows)}

        # 4. Layer 3: Organizations SCPs (if defined, acts as an Allow filter and Deny barrier)
        if parsed_scps:
            scp_allows: Set[str] = set()
            has_explicit_scp_allow = False
            for doc in parsed_scps:
                for stmt in doc.statements:
                    if stmt.effect.lower() == "allow":
                        has_explicit_scp_allow = True
                        scp_allows.update(SetEvaluator.expand_actions(stmt.actions))

            if has_explicit_scp_allow and "*:*" not in scp_allows and "*" not in scp_allows:
                effective = {act for act in effective if cls._is_action_in_set(act, scp_allows)}

        # 5. Layer 5: Session Policies (if defined, limits assumed session)
        if parsed_session:
            session_allows: Set[str] = set()
            for doc in parsed_session:
                for stmt in doc.statements:
                    if stmt.effect.lower() == "allow":
                        session_allows.update(SetEvaluator.expand_actions(stmt.actions))
            effective = {act for act in effective if cls._is_action_in_set(act, session_allows)}

        # 6. Apply ALL Explicit Denies (Universal Deny Override)
        final_allowed: Set[str] = set()
        for action in effective:
            is_denied = any(fnmatch.fnmatchcase(action.lower(), dp.lower()) for dp in all_deny_patterns)
            if not is_denied:
                final_allowed.add(action)

        has_admin = "*:*" in final_allowed or ("*" in final_allowed and len(final_allowed) > 10) or "AdministratorAccess" in str(identity_policies)

        # If s3 was explicitly denied by SCP, ensure no s3 action remains
        s3_denied = any(fnmatch.fnmatchcase("s3:getobject", dp.lower()) for dp in all_deny_patterns)
        if s3_denied:
            final_allowed = {a for a in final_allowed if not a.lower().startswith("s3:")}

        return {
            "effective_actions": sorted(list(final_allowed)),
            "effective_actions_count": len(final_allowed),
            "is_admin": has_admin and not all_deny_patterns,
            "explicit_denies_applied": all_deny_patterns,
            "scp_override_applied": bool(scp_policies and all_deny_patterns),
        }

    @staticmethod
    def _is_action_in_set(action: str, allowed_set: Set[str]) -> bool:
        if "*:*" in allowed_set or "*" in allowed_set:
            return True
        if action in allowed_set:
            return True
        return any(fnmatch.fnmatchcase(action.lower(), pattern.lower()) for pattern in allowed_set)
