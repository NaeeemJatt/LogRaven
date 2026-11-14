"""Module 10: KSPM & Kubernetes Admission Controller (KAC) Webhook.

FastAPI Router and Kubernetes Admission Webhook Server (PRD-MOD-10).
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from services.mod10_kspm_kac.internal.k8s_crawler.network_policy_audit import NetworkPolicyAuditor
from services.mod10_kspm_kac.internal.k8s_crawler.rbac_auditor import RBACAuditor
from services.mod10_kspm_kac.internal.pss_evaluator.capabilities_filter import CapabilitiesFilter
from services.mod10_kspm_kac.internal.pss_evaluator.privileged_checker import PrivilegedChecker
from services.mod10_kspm_kac.internal.pss_evaluator.root_user_checker import RootUserChecker
from services.mod10_kspm_kac.internal.pss_evaluator.socket_mount_checker import SocketMountChecker
from services.mod10_kspm_kac.internal.repository.kspm_repo import KSPMRepository
from services.mod10_kspm_kac.internal.webhook_handler.request_parser import AdmissionRequestParser
from services.mod10_kspm_kac.internal.webhook_handler.response_builder import AdmissionResponseBuilder

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Module 10: KSPM & Kubernetes Admission Controller"])


# ── Request / Response Models ─────────────────────────────────────────────

class RegisterClusterRequest(BaseModel):
    asset_urn: str
    cluster_name: str
    distribution: str = "EKS"
    k8s_version: str = "v1.30.0"
    kac_webhook_installed: bool = True
    kac_enforcement_mode: str = "AUDIT"
    namespaces_count: int = 5
    pods_count: int = 42


class AuditRBACRequest(BaseModel):
    role_name: str
    rules: List[Dict[str, Any]]
    is_cluster_scoped: bool = True


class AuditNetworkPolicyRequest(BaseModel):
    namespace: str
    network_policies: List[Dict[str, Any]] = Field(default_factory=list)


# ── Webhook Core Evaluation Function ─────────────────────────────────────

def evaluate_pod_spec_all_rules(pod_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Runs all KSPM and Pod Security Standard evaluators against a pod spec."""
    findings = []
    findings.extend(PrivilegedChecker.evaluate_pod_spec(pod_spec))
    findings.extend(SocketMountChecker.evaluate_pod_spec(pod_spec))
    findings.extend(RootUserChecker.evaluate_pod_spec(pod_spec))
    findings.extend(CapabilitiesFilter.evaluate_pod_spec(pod_spec))
    return findings


# ── REST API / Webhook Endpoints ─────────────────────────────────────────

@router.post("/validate")
async def validate_admission_review(
    review_payload: Dict[str, Any],
    mode: Optional[str] = Query(None, description="Override enforcement mode: ENFORCE or AUDIT"),
    db: Optional[AsyncSession] = Depends(get_db),
):
    """Kubernetes ValidatingAdmissionWebhook endpoint (admission.k8s.io/v1).

    Intercepts AdmissionReview payloads, evaluates against PSS & custom rules,
    and returns allowed: True/False with appropriate status and warnings.
    """
    try:
        uid, kind, name, namespace, operation, pod_spec, dry_run = AdmissionRequestParser.parse_review(review_payload)
    except Exception as err:
        logger.error(f"Failed to parse AdmissionReview: {err}")
        return {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "allowed": False,
                "status": {"code": 400, "message": f"Malformed AdmissionReview: {str(err)}"},
            },
        }

    # Evaluate rules
    findings = evaluate_pod_spec_all_rules(pod_spec)

    # Determine enforcement mode: query param override -> annotation -> default ENFORCE
    enforcement_mode = mode or "ENFORCE"
    metadata = review_payload.get("request", {}).get("object", {}).get("metadata", {}) or {}
    annotations = metadata.get("annotations", {}) or {}
    if "lograven.io/kac-mode" in annotations:
        enforcement_mode = annotations["lograven.io/kac-mode"].upper()

    response = AdmissionResponseBuilder.build_response(
        uid=uid,
        findings=findings,
        enforcement_mode=enforcement_mode,
    )

    return response


@router.post("/audit/rbac")
async def audit_rbac_role(
    req: AuditRBACRequest,
    current_user: User = Depends(get_current_user),
):
    """Audits Kubernetes Role or ClusterRole permissions for wildcards and escalation risks."""
    findings = RBACAuditor.audit_cluster_role(
        role_name=req.role_name,
        rules=req.rules,
        is_cluster_scoped=req.is_cluster_scoped,
    )
    return {
        "role_name": req.role_name,
        "is_cluster_scoped": req.is_cluster_scoped,
        "total_findings": len(findings),
        "findings": findings,
        "is_compliant": len(findings) == 0,
    }


@router.post("/audit/network-policy")
async def audit_network_policy(
    req: AuditNetworkPolicyRequest,
    current_user: User = Depends(get_current_user),
):
    """Audits namespace network policies to verify default-deny microsegmentation."""
    findings = NetworkPolicyAuditor.audit_namespace_network_policies(
        namespace=req.namespace,
        network_policies=req.network_policies,
    )
    return {
        "namespace": req.namespace,
        "total_findings": len(findings),
        "findings": findings,
        "has_default_deny": len(findings) == 0,
    }


@router.post("/clusters")
async def register_cluster(
    req: RegisterClusterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers or updates a monitored Kubernetes cluster in inventory."""
    tenant_id = getattr(current_user, "tenant_id", None)
    cluster = await KSPMRepository.upsert_cluster(
        session=db,
        asset_urn=req.asset_urn,
        cluster_name=req.cluster_name,
        distribution=req.distribution,
        k8s_version=req.k8s_version,
        kac_webhook_installed=req.kac_webhook_installed,
        kac_enforcement_mode=req.kac_enforcement_mode,
        namespaces_count=req.namespaces_count,
        pods_count=req.pods_count,
        tenant_id=tenant_id,
    )
    await db.commit()
    return {
        "id": str(cluster.id),
        "asset_urn": cluster.asset_urn,
        "cluster_name": cluster.cluster_name,
        "distribution": cluster.distribution,
        "k8s_version": cluster.k8s_version,
        "kac_webhook_installed": cluster.kac_webhook_installed,
        "kac_enforcement_mode": cluster.kac_enforcement_mode,
        "namespaces_count": cluster.namespaces_count,
        "pods_count": cluster.pods_count,
    }


@router.get("/clusters")
async def list_clusters(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists monitored Kubernetes clusters."""
    clusters = await KSPMRepository.list_clusters(db, limit=limit, offset=offset)
    return {
        "total": len(clusters),
        "clusters": [
            {
                "id": str(c.id),
                "asset_urn": c.asset_urn,
                "cluster_name": c.cluster_name,
                "distribution": c.distribution,
                "k8s_version": c.k8s_version,
                "kac_webhook_installed": c.kac_webhook_installed,
                "kac_enforcement_mode": c.kac_enforcement_mode,
                "namespaces_count": c.namespaces_count,
                "pods_count": c.pods_count,
                "last_crawled_at": c.last_crawled_at.isoformat() if c.last_crawled_at else None,
            }
            for c in clusters
        ],
    }


@router.get("/admission-events")
async def list_admission_events(
    cluster_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists admission review decisions."""
    events = await KSPMRepository.list_admission_events(db, cluster_id=cluster_id, limit=limit, offset=offset)
    return {
        "total": len(events),
        "events": [
            {
                "id": str(e.id),
                "cluster_id": str(e.cluster_id),
                "resource_kind": e.resource_kind,
                "resource_name": e.resource_name,
                "namespace": e.namespace,
                "operation": e.operation,
                "allowed": e.allowed,
                "violated_policies": e.violated_policies,
                "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
            }
            for e in events
        ],
    }
