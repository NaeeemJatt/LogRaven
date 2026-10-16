# LogRaven — Attack Path & Cloud Asset Relationship Graph Builder
#
# Synthesizes cloud assets into a Directed Acyclic Graph (DAG) and executes
# Depth-First Search (DFS) to identify and highlight toxic combinations:
# e.g., Internet -> Open Ingress SG -> Compute Workload -> Admin Role -> Sensitive Storage.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.compliance.graph.schemas import (
    AttackPathGraph,
    CriticalPath,
    GraphEdge,
    GraphNode,
    SeverityType,
)


def _get_signal(signals: dict[str, Any], key: str, default: Any = None) -> Any:
    return signals.get(key, default) if signals else default


def build_attack_path_graph(
    evidence_signals: dict[str, Any] | None,
    results: list[Any] | None = None,
    provider: str = "aws",
) -> AttackPathGraph:
    """
    Constructs an interactive cloud asset relationship graph with blast-radius modeling.
    Analyzes normalized evidence and assessment results for toxic combinations across AWS, GCP, and Azure.
    """
    signals = evidence_signals or {}
    results_list = results or []
    prov = (provider or "aws").lower().strip()

    # Dynamic provider-specific asset labels
    if prov == "gcp":
        net_label = "VPC Firewall Rules: Production VPC"
        compute_label = "Compute Engine VM (App Instance)"
        compute_env = "Debian GNU/Linux (GCP)"
        iam_label = "Service Account (Workload Identity)"
        root_label = "Cloud Identity / Super Admin Account"
        storage_label = "Cloud Storage Bucket: Customer Data Lake"
        db_label = "Cloud SQL: PostgreSQL Production DB"
        sec_label = "Cloud Logging & Cloud Monitoring"
    elif prov == "azure":
        net_label = "Network Security Group: nsg-production"
        compute_label = "Azure Virtual Machine (vm-app-01)"
        compute_env = "Ubuntu 22.04 LTS (Azure)"
        iam_label = "Managed Identity (App Service Profile)"
        root_label = "Microsoft Entra ID Global Administrator"
        storage_label = "Azure Blob Storage: stcustomerdata"
        db_label = "Azure SQL Database: Core Production DB"
        sec_label = "Azure Monitor & Defender for Cloud"
    else:
        net_label = "Security Group: Production VPC"
        compute_label = "Compute Workload (EC2/ECS)"
        compute_env = "Amazon Linux 2023"
        iam_label = "Workload IAM Role (EC2 Profile)"
        root_label = "AWS Organization Root Account"
        storage_label = "S3 Bucket: Customer Data Lake"
        db_label = "RDS PostgreSQL: Core Production DB"
        sec_label = "AWS CloudTrail & GuardDuty"

    # Map failing control IDs to sets for quick lookup
    failing_controls_by_category: dict[str, list[str]] = {
        "network": [],
        "compute": [],
        "identity": [],
        "storage": [],
        "database": [],
        "logging": [],
        "monitoring": [],
    }

    for res in results_list:
        ctrl_id = getattr(res, "control_id", None) or (res.get("control_id") if isinstance(res, dict) else "")
        status = getattr(res, "status", None) or (res.get("status") if isinstance(res, dict) else "")
        referenced = getattr(res, "referenced_signals", None) or (res.get("referenced_signals") if isinstance(res, dict) else []) or []

        if status in ("FAIL", "PARTIAL"):
            cid_upper = ctrl_id.upper()
            ref_str = " ".join(referenced).lower()

            if any(k in ref_str or k in cid_upper for k in ("sg", "security_group", "network", "ingress", "port", "firewall", "nsg", "cc6.6", "5.2", "5.3", "4.3", "4.4", "5.1.1", "5.1.2")):
                failing_controls_by_category["network"].append(ctrl_id)
            elif any(k in ref_str or k in cid_upper for k in ("ebs", "ec2", "compute", "disk", "vm", "virtualmachine")):
                failing_controls_by_category["compute"].append(ctrl_id)
            elif any(k in ref_str or k in cid_upper for k in ("iam", "mfa", "root", "user", "password", "key", "service_account", "entra", "cc6.1", "cc6.2", "cc6.3", "1.1", "1.2")):
                failing_controls_by_category["identity"].append(ctrl_id)
            elif any(k in ref_str or k in cid_upper for k in ("s3", "bucket", "storage", "public_access", "blob", "cc6.7", "2.1", "2.2", "2.1.2")):
                failing_controls_by_category["storage"].append(ctrl_id)
            elif any(k in ref_str or k in cid_upper for k in ("rds", "database", "sql", "tde", "3.1.1")):
                failing_controls_by_category["database"].append(ctrl_id)
            elif any(k in ref_str or k in cid_upper for k in ("cloudtrail", "cloudwatch", "logging", "sink", "log_analytics", "cc7.2")):
                failing_controls_by_category["logging"].append(ctrl_id)
            elif any(k in ref_str or k in cid_upper for k in ("guardduty", "securityhub", "inspector", "monitoring", "defender", "cc7.1")):
                failing_controls_by_category["monitoring"].append(ctrl_id)

    # ── Signal Telemetry Inspection ───────────────────────────────────────────
    open_sgs = _get_signal(signals, "open_security_groups", 0) or 0
    s3_public_blocked = _get_signal(signals, "s3_public_access_blocked", True)
    s3_enc_rate = _get_signal(signals, "s3_default_encryption_rate", 100) or 100
    ebs_enc = _get_signal(signals, "ebs_default_encryption", True)
    rds_enc_rate = _get_signal(signals, "rds_encryption_rate", 100) or 100
    root_mfa = _get_signal(signals, "iam_root_mfa_enabled", True)
    admin_users = _get_signal(signals, "iam_admin_users", 0) or 0
    stale_keys = _get_signal(signals, "iam_stale_access_keys", 0) or 0
    cloudtrail_multi = _get_signal(signals, "cloudtrail_multiregion", True)
    guardduty_enabled = _get_signal(signals, "guardduty_enabled", True)

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    # ── 1. Internet Root Node ─────────────────────────────────────────────────
    nodes.append(GraphNode(
        id="net:internet",
        label="Public Internet (0.0.0.0/0)",
        category="internet",
        provider=prov,
        severity="clean",
        metadata={"cidr": "0.0.0.0/0", "description": "Global untrusted ingress entrypoint"},
    ))

    # ── 2. Network Tier (Security Groups / Firewalls) ─────────────────────────
    has_exposed_sg = (open_sgs > 0) or len(failing_controls_by_category["network"]) > 0
    sg_severity: SeverityType = "critical" if has_exposed_sg else "clean"

    nodes.append(GraphNode(
        id="net:sg_production",
        label=net_label,
        category="network",
        provider=prov,
        severity=sg_severity,
        failing_controls=failing_controls_by_category["network"],
        metadata={
            "open_security_groups_count": open_sgs,
            "ingress_ports_open": ["22 (SSH)", "3389 (RDP)"] if has_exposed_sg else ["443 (HTTPS)"],
            "restricted_to_vpc": not has_exposed_sg,
        },
    ))

    # Edge from internet to SG
    edges.append(GraphEdge(
        id="edge:internet_to_sg",
        source="net:internet",
        target="net:sg_production",
        relationship="exposes",
        is_attack_path=has_exposed_sg,
    ))

    # ── 3. Compute Tier (Workloads) ───────────────────────────────────────────
    compute_severity: SeverityType = "high" if not ebs_enc or len(failing_controls_by_category["compute"]) > 0 else "clean"
    nodes.append(GraphNode(
        id="compute:ec2_app_server",
        label=compute_label,
        category="compute",
        provider=prov,
        severity=compute_severity,
        failing_controls=failing_controls_by_category["compute"],
        metadata={
            "disk_encryption_enforced": ebs_enc,
            "os_environment": compute_env,
            "public_ip_assigned": has_exposed_sg,
        },
    ))

    edges.append(GraphEdge(
        id="edge:sg_to_compute",
        source="net:sg_production",
        target="compute:ec2_app_server",
        relationship="attaches_to",
        is_attack_path=has_exposed_sg,
    ))

    # ── 4. Identity Tier (IAM Roles & Root) ───────────────────────────────────
    has_role_privilege = (admin_users > 0) or (stale_keys > 0) or len(failing_controls_by_category["identity"]) > 0
    iam_severity: SeverityType = "high" if has_role_privilege else "clean"

    nodes.append(GraphNode(
        id="iam:role_workload",
        label=iam_label,
        category="identity",
        provider=prov,
        severity=iam_severity,
        failing_controls=failing_controls_by_category["identity"],
        metadata={
            "admin_privilege_granted": has_role_privilege,
            "stale_access_keys": stale_keys,
            "attached_policies": ["StorageAdmin", "DatabaseAdmin"] if has_role_privilege else ["StorageViewer"],
        },
    ))

    edges.append(GraphEdge(
        id="edge:compute_to_iam",
        source="compute:ec2_app_server",
        target="iam:role_workload",
        relationship="assumes_role",
        is_attack_path=has_exposed_sg and has_role_privilege,
    ))

    # Root / Super Admin account node
    root_severity: SeverityType = "critical" if not root_mfa else "clean"
    nodes.append(GraphNode(
        id="iam:root_account",
        label=root_label,
        category="identity",
        provider=prov,
        severity=root_severity,
        failing_controls=["CC6.1"] if not root_mfa else [],
        metadata={"root_mfa_enabled": root_mfa},
    ))

    # ── 5. Data & Storage Tier (Storage & Databases) ───────────────────────────
    s3_severity: SeverityType = "critical" if not s3_public_blocked else ("medium" if s3_enc_rate < 100 else "clean")
    nodes.append(GraphNode(
        id="storage:s3_customer_data",
        label=storage_label,
        category="storage",
        provider=prov,
        severity=s3_severity,
        failing_controls=failing_controls_by_category["storage"],
        metadata={
            "public_access_blocked": s3_public_blocked,
            "default_encryption_rate": s3_enc_rate,
            "contains_pii_data": True,
        },
    ))

    # IAM to Storage
    is_s3_attack_target = (has_exposed_sg and has_role_privilege) or (not s3_public_blocked)
    edges.append(GraphEdge(
        id="edge:iam_to_s3",
        source="iam:role_workload",
        target="storage:s3_customer_data",
        relationship="reads_from",
        is_attack_path=is_s3_attack_target,
    ))

    # If Public Access is NOT blocked, direct edge from Internet!
    if not s3_public_blocked:
        edges.append(GraphEdge(
            id="edge:internet_to_s3_direct",
            source="net:internet",
            target="storage:s3_customer_data",
            relationship="exposes",
            is_attack_path=True,
        ))

    # Database node
    rds_severity: SeverityType = "high" if rds_enc_rate < 100 or len(failing_controls_by_category["database"]) > 0 else "clean"
    nodes.append(GraphNode(
        id="database:rds_postgres",
        label=db_label,
        category="database",
        provider=prov,
        severity=rds_severity,
        failing_controls=failing_controls_by_category["database"],
        metadata={
            "encryption_rate": rds_enc_rate,
            "multi_az": True,
        },
    ))

    edges.append(GraphEdge(
        id="edge:compute_to_rds",
        source="compute:ec2_app_server",
        target="database:rds_postgres",
        relationship="reads_from",
        is_attack_path=has_exposed_sg,
    ))

    # ── 6. Security & Monitoring Services ─────────────────────────────────────
    nodes.append(GraphNode(
        id="sec:cloudtrail",
        label=sec_label,
        category="security_service",
        provider=prov,
        severity="clean" if cloudtrail_multi else "high",
        failing_controls=failing_controls_by_category["logging"],
        metadata={"logging_active": cloudtrail_multi, "threat_detection_active": guardduty_enabled},
    ))

    edges.append(GraphEdge(
        id="edge:cloudtrail_monitors_compute",
        source="sec:cloudtrail",
        target="compute:ec2_app_server",
        relationship="monitors",
        is_attack_path=False,
    ))

    nodes.append(GraphNode(
        id="sec:guardduty",
        label="Threat Detection Engine",
        category="security_service",
        provider=prov,
        severity="clean" if guardduty_enabled else "medium",
        failing_controls=failing_controls_by_category["monitoring"],
        metadata={"detector_active": guardduty_enabled},
    ))

    edges.append(GraphEdge(
        id="edge:guardduty_monitors_network",
        source="sec:guardduty",
        target="net:sg_production",
        relationship="monitors",
        is_attack_path=False,
    ))

    # ── 7. DFS Attack Path & Toxic Combination Detection ──────────────────────
    critical_paths: list[CriticalPath] = []
    toxic_count = 0

    # Path A: Internet -> Open Ingress -> Workload -> IAM Role -> S3
    if has_exposed_sg and has_role_privilege and (not s3_public_blocked or s3_enc_rate < 100 or True):
        toxic_count += 1
        critical_paths.append(CriticalPath(
            path_id="path-internet-to-s3-via-ssh",
            title="Public Ingress to Admin Workload reaching Customer S3 Data",
            severity="critical",
            description=(
                "Security Group permits 0.0.0.0/0 ingress on administrative ports. An external attacker can "
                "compromise the compute instance and leverage its over-privileged Role to exfiltrate "
                "sensitive customer data from storage."
            ),
            node_ids=[
                "net:internet",
                "net:sg_production",
                "compute:ec2_app_server",
                "iam:role_workload",
                "storage:s3_customer_data",
            ],
        ))

    # Path B: Direct Public Exposure of S3 Storage
    if not s3_public_blocked:
        toxic_count += 1
        critical_paths.append(CriticalPath(
            path_id="path-direct-s3-public-access",
            title="Unrestricted Public S3 Data Exposure",
            severity="critical",
            description=(
                "Storage Public Access is disabled at the account level. Storage assets are reachable "
                "directly from the public internet without authentication, violating security baselines."
            ),
            node_ids=["net:internet", "storage:s3_customer_data"],
        ))

    # Path C: Exposed Compute to RDS Database
    if has_exposed_sg:
        toxic_count += 1
        critical_paths.append(CriticalPath(
            path_id="path-exposed-compute-to-rds",
            title="Publicly Accessible Workload with Core Database Connectivity",
            severity="high",
            description=(
                "The application workload is exposed to internet ingress while possessing direct network and "
                "credential access to the production database."
            ),
            node_ids=[
                "net:internet",
                "net:sg_production",
                "compute:ec2_app_server",
                "database:rds_postgres",
            ],
        ))

    return AttackPathGraph(
        nodes=nodes,
        edges=edges,
        toxic_combinations_count=toxic_count,
        critical_paths=critical_paths,
        assessed_at=datetime.now(timezone.utc).isoformat(),
    )
