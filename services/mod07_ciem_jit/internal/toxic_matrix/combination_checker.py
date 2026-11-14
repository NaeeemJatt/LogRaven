"""Toxic Permission Combination Checker (FR-MOD7-02, TC-MOD7-002).

Evaluates whether a principal's effective granted actions satisfy any of the
21 cataloged cloud privilege escalation vectors.
"""

import fnmatch
from typing import Any, Dict, List, Set

from services.mod07_ciem_jit.internal.toxic_matrix.privesc_catalog import PRIVESC_CATALOG, PrivEscVector


class ToxicCombinationChecker:
    """Evaluates effective permissions for privilege escalation vectors."""

    @classmethod
    def evaluate_principal_actions(
        cls,
        granted_actions: List[str],
        provider: str = "aws",
    ) -> Dict[str, Any]:
        """Matches granted actions against privilege escalation vectors (TC-MOD7-002)."""
        prov_lower = provider.lower()
        granted_set = {a.lower() for a in granted_actions}
        has_wildcard_all = "*:*" in granted_set or "*" in granted_set

        detected_vectors: List[Dict[str, Any]] = []

        for vector in PRIVESC_CATALOG:
            if vector.cloud_provider != prov_lower and prov_lower != "all":
                continue

            # Check if all required actions are satisfied by the granted actions
            all_satisfied = True
            for req in vector.required_actions:
                req_lower = req.lower()
                if has_wildcard_all:
                    continue

                # Check exact or wildcard match
                satisfied = any(
                    cls._matches(granted_action, req_lower)
                    for granted_action in granted_set
                )
                if not satisfied:
                    all_satisfied = False
                    break

            if all_satisfied:
                detected_vectors.append({
                    "vector_id": vector.id,
                    "title": vector.title,
                    "severity": vector.severity,
                    "required_actions": vector.required_actions,
                    "description": vector.description,
                    "mitigation": vector.mitigation,
                })

        has_toxic = len(detected_vectors) > 0
        return {
            "has_toxic_combinations": has_toxic,
            "toxic_vectors_count": len(detected_vectors),
            "toxic_vectors": detected_vectors,
            "vector_ids": [v["vector_id"] for v in detected_vectors],
        }

    @staticmethod
    def _matches(pattern: str, action: str) -> bool:
        if pattern in ("*", "*:*"):
            return True
        return fnmatch.fnmatchcase(action, pattern)
