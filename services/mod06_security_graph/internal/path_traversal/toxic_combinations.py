"""Toxic Combinations Detector (PRD-MOD-06, FR-MOD6-03).

Identifies hazardous multi-domain intersections:
e.g. Internet Exposure + Open Port 22 + Critical CVE / eBPF In-Memory Reachability + Admin IAM Role -> Crown Jewel.
"""

from typing import Any, Dict, List, Optional
from services.mod06_security_graph.internal.truerisk_engine.calculator import TrueRiskCalculator


class ToxicCombinationDetector:
    """Detects multi-domain toxic security conditions that yield imminent exploit paths."""

    @staticmethod
    def inspect_node_toxic_state(
        node_id: str,
        node_data: Dict[str, Any],
        connected_edges: List[Dict[str, Any]],
        neighbor_nodes: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Evaluates whether an individual node participates in a toxic combination."""
        meta = node_data.get("metadata", {})
        is_internet = node_data.get("is_internet_facing", False) or meta.get("has_open_ingress", False)
        has_vuln = meta.get("cve_count", 0) > 0 or meta.get("has_critical_vuln", False)

        # Check attached roles and targets
        has_admin_role = False
        reaches_crown_jewel = False
        crown_jewels = []

        for e in connected_edges:
            tgt_id = e["target_id"]
            tgt_node = neighbor_nodes.get(tgt_id, {})
            tgt_meta = tgt_node.get("metadata", {})

            if tgt_node.get("domain") == "IDENTITY" and (tgt_meta.get("is_admin") or "admin" in tgt_id.lower()):
                has_admin_role = True

            if tgt_meta.get("is_crown_jewel") or tgt_meta.get("has_pii") or tgt_node.get("domain") == "DATA":
                reaches_crown_jewel = True
                crown_jewels.append(tgt_id)

        if is_internet and (has_vuln or has_admin_role):
            severity = "CRITICAL" if (has_vuln and has_admin_role and reaches_crown_jewel) else "HIGH"
            evaluation = TrueRiskCalculator.evaluate(
                misconfig_severity="CRITICAL" if has_vuln else "HIGH",
                network_exposure="DIRECT_INTERNET" if is_internet else "INTERNAL_VPC",
                identity_role="ADMIN" if has_admin_role else "BROAD_RW",
                data_classification="PII_PCI_HIPAA" if reaches_crown_jewel else "BUSINESS_DATA",
                threat_status="ACTIVE_IOA" if reaches_crown_jewel else "NONE",
            )

            return {
                "node_id": node_id,
                "label": node_data.get("label", node_id),
                "toxic_type": "INTERNET_EXPOSED_VULNERABLE_ADMIN",
                "severity": severity,
                "truerisk_score": evaluation["truerisk_score"],
                "reaches_crown_jewel": reaches_crown_jewel,
                "crown_jewels": crown_jewels,
                "description": (
                    f"Toxic Combination Detected: Asset {node_id} has direct public Internet exposure, "
                    f"vulnerabilities, and administrative IAM credentials reaching Crown Jewel storage."
                ),
            }

        return None
