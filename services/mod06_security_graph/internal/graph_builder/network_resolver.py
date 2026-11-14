"""Effective Network Exposure Calculator (PRD-MOD-06, FR-MOD6-02).

Evaluates whether an asset is reachable from the public Internet by traversing:
1. Public Elastic IPs / Public DNS
2. VPC Route Tables (0.0.0.0/0 directed to Internet Gateways)
3. Security Group / Network ACL ingress rules allowing 0.0.0.0/0
"""

from typing import Any, Dict, List, Optional, Tuple


class NetworkExposureResolver:
    """Calculates boolean is_internet_facing and effective exposure score E_reach."""

    @staticmethod
    def evaluate_security_group_ingress(
        ingress_rules: List[Dict[str, Any]],
    ) -> Tuple[bool, List[int]]:
        """Checks if any ingress rule allows unrestricted access (0.0.0.0/0 or ::/0)."""
        has_public_ingress = False
        open_ports: List[int] = []

        for rule in ingress_rules:
            cidrs = rule.get("CidrIp", rule.get("cidr_ip", []))
            if isinstance(cidrs, str):
                cidrs = [cidrs]

            is_open = any(c in ("0.0.0.0/0", "::/0") for c in cidrs)
            if is_open:
                has_public_ingress = True
                from_port = rule.get("FromPort", rule.get("from_port"))
                to_port = rule.get("ToPort", rule.get("to_port"))
                if from_port is not None and to_port is not None:
                    if from_port == to_port:
                        open_ports.append(from_port)
                    else:
                        open_ports.extend([from_port, to_port])

        return has_public_ingress, sorted(list(set(open_ports)))

    @classmethod
    def resolve_exposure(
        cls,
        has_public_ip: bool = False,
        has_igw_route: bool = False,
        ingress_rules: Optional[List[Dict[str, Any]]] = None,
        is_behind_load_balancer: bool = False,
        is_internal_vpc: bool = True,
    ) -> Dict[str, Any]:
        """Calculates effective exposure classification and E_reach score."""
        has_open_sg, open_ports = cls.evaluate_security_group_ingress(ingress_rules or [])

        # Direct internet: has public IP, IGW route, AND open security group ingress
        if (has_public_ip or has_igw_route) and has_open_sg:
            return {
                "exposure_tier": "DIRECT_INTERNET",
                "e_reach": 100.0,
                "is_internet_facing": True,
                "open_ports": open_ports,
                "reason": "Direct public IP/route with 0.0.0.0/0 security group ingress",
            }

        # Behind public load balancer or reverse proxy
        if is_behind_load_balancer and has_open_sg:
            return {
                "exposure_tier": "LOAD_BALANCER_PROXY",
                "e_reach": 60.0,
                "is_internet_facing": True,
                "open_ports": open_ports,
                "reason": "Routed through public Load Balancer / Reverse Proxy",
            }

        # Internal VPC subnet (accessible only laterally or via VPN/peering)
        if is_internal_vpc:
            return {
                "exposure_tier": "INTERNAL_VPC",
                "e_reach": 25.0,
                "is_internet_facing": False,
                "open_ports": open_ports,
                "reason": "Internal VPC private subnet without direct public ingress",
            }

        # Fully isolated
        return {
            "exposure_tier": "ISOLATED",
            "e_reach": 0.0,
            "is_internet_facing": False,
            "open_ports": [],
            "reason": "Completely isolated host/workload",
        }

