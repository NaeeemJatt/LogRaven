# LogRaven — Deterministic CSPM & AWS Log Engine FastAPI Router
# Provides 100% Deterministic (Non-AI) Compliance Evaluation,
# CloudTrail Mutating Drift Ingestion, and Catalog Summaries.

from __future__ import annotations

from datetime import date, datetime, timezone
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.aws_collector import AWSStateAndLogCollector
from app.compliance.deterministic_grader import DeterministicComplianceGrader
from app.compliance.frameworks.base import (
    list_mandates,
    list_policies,
)
from app.dependencies import get_current_user, get_db, oauth2_scheme, access_cookie_scheme
from app.limiter import limiter
from app.models.soc2_audit import AuditJob, AuditResult, ComplianceSnapshot
from app.models.user import User
from app.rules.engine import RuleEngine
from app.rules.loader import RuleLoader, get_default_rule_loader
from app.rules.schema import DeterministicRuleSpec
from app.utils.logger import get_logger

logger = get_logger("lograven.api.cspm")

router = APIRouter()

async def get_optional_current_user(
    bearer_token: str | None = Depends(oauth2_scheme),
    cookie_token: str | None = Depends(access_cookie_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    try:
        return await get_current_user(bearer_token=bearer_token, cookie_token=cookie_token, db=db)
    except Exception:
        return None

# Cached engine instance for sub-millisecond evaluation
_CACHED_ENGINE: Optional[RuleEngine] = None


def get_engine() -> RuleEngine:
    global _CACHED_ENGINE
    if _CACHED_ENGINE is None:
        loader = get_default_rule_loader()
        _CACHED_ENGINE = RuleEngine(loader=loader)
    return _CACHED_ENGINE


# ── Pydantic Request & Response Schemas ──────────────────────────────────────


class NonAIEvalRequest(BaseModel):
    provider: str = Field(default="AWS", description="Cloud provider (AWS, AZURE, GCP, OCI)")
    resources_by_service: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        default_factory=dict,
        description="Dictionary mapping service name (IAM, EC2, VPC, S3, KMS) to lists of resource configs",
    )
    cloudtrail_events: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Optional list of CloudTrail events to ingest and evaluate for drift and log controls",
    )
    account_id: Optional[str] = Field(default=None, description="Cloud account ID or alias")
    session_id: Optional[str] = Field(default=None, description="Audit session identifier")


class LogIngestRequest(BaseModel):
    provider: str = Field(default="AWS", description="Cloud provider (AWS)")
    events: List[Dict[str, Any]] = Field(..., description="Batch of CloudTrail / audit log events")


class CollectAndEvalAWSRequest(BaseModel):
    region_name: str = Field(default="us-east-1", description="AWS Region")
    services: Optional[List[str]] = Field(
        default=None,
        description="Specific services to collect (e.g. ['IAM', 'EC2', 'S3', 'KMS'])",
    )
    max_cloudtrail_events: int = Field(default=50, ge=1, le=500, description="Max CloudTrail events to fetch")


# ── Route Endpoints ──────────────────────────────────────────────────────────


@router.post("/evaluate/non-ai", summary="Execute 100% Deterministic CSPM Evaluation")
def evaluate_non_ai(request: NonAIEvalRequest) -> Dict[str, Any]:
    """
    Evaluates cloud configuration state and CloudTrail events without AI hallucination.
    Guarantees sub-millisecond per-control execution, 12 pure-Python operators,
    real-time mutating drift detection, and full Policy/Mandate rollups.
    """
    t0 = time.perf_counter()
    session_id = request.session_id or str(uuid.uuid4())
    provider = request.provider.upper()

    engine = get_engine()
    grader = DeterministicComplianceGrader(loader=engine.loader)

    # 1. Evaluate mutating drift and runtime log controls on CloudTrail events
    drift_alerts: List[Dict[str, Any]] = []
    log_alerts: List[Dict[str, Any]] = []

    if request.cloudtrail_events:
        for evt in request.cloudtrail_events:
            alerts = engine.process_cloudtrail_event(evt)
            for a in alerts:
                if a.get("detection_mode") == "CLOUDTRAIL_INLINE_DRIFT":
                    drift_alerts.append(a)
                else:
                    log_alerts.append(a)

    # 2. Normalize resource service keys to uppercase
    normalized_resources: Dict[str, List[Dict[str, Any]]] = {}
    if request.resources_by_service:
        for svc, res_list in request.resources_by_service.items():
            normalized_resources[svc.upper()] = res_list

    # 3. Deterministic compliance grading across all controls, policies, and mandates
    grading_results = grader.evaluate_all_without_ai(
        provider=provider,
        resources_by_service=normalized_resources,
        cloudtrail_events=request.cloudtrail_events or [],
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "status": "success",
        "session_id": session_id,
        "account_id": request.account_id or "default-account",
        "provider": provider,
        "non_ai_guarantee": True,
        "execution_summary": {
            "total_controls_evaluated": grading_results["total_controls_evaluated"],
            "controls_passed": grading_results["controls_passed"],
            "controls_failed": grading_results["controls_failed"],
            "drift_alerts_detected": len(drift_alerts),
            "log_alerts_detected": len(log_alerts),
            "latency_ms": elapsed_ms,
        },
        "policies": grading_results["policies"],
        "mandates": grading_results["mandates"],
        "controls": grading_results["controls"],
        "drift_alerts": drift_alerts,
        "log_alerts": log_alerts,
    }


@router.post("/ingest-logs", summary="Ingest CloudTrail Logs for Mutating Drift & Log Controls")
def ingest_logs(request: LogIngestRequest) -> Dict[str, Any]:
    """
    Ingests raw CloudTrail events and runs real-time mutating drift detection
    (e.g., PutRolePolicy -> CID 50, AuthorizeSecurityGroupIngress -> CID 41/42, PutBucketAcl)
    and sliding-window log controls (CID 18, 27-40).
    """
    t0 = time.perf_counter()
    engine = get_engine()

    drift_alerts: List[Dict[str, Any]] = []
    log_alerts: List[Dict[str, Any]] = []

    for evt in request.events:
        hits = engine.process_cloudtrail_event(evt)
        for h in hits:
            if h.get("detection_mode") == "CLOUDTRAIL_INLINE_DRIFT":
                drift_alerts.append(h)
            else:
                log_alerts.append(h)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "status": "success",
        "non_ai_guarantee": True,
        "processed_events": len(request.events),
        "drift_alerts_count": len(drift_alerts),
        "log_alerts_count": len(log_alerts),
        "drift_alerts": drift_alerts,
        "log_alerts": log_alerts,
        "latency_ms": elapsed_ms,
    }


@router.get("/catalogs/summary", summary="Retrieve Catalog and Engine Summary")
def get_catalogs_summary() -> Dict[str, Any]:
    """
    Returns summary statistics for the deterministic rule engine, catalog sizes,
    indexed CIDs, registered policies, and mandates.
    """
    engine = get_engine()
    loader = engine.loader

    # Count rules by provider
    provider_counts: Dict[str, int] = {}
    for r in loader.rules_by_id.values():
        prov = r.provider.upper()
        provider_counts[prov] = provider_counts.get(prov, 0) + 1

    policies = list_policies()
    mandates = list_mandates()

    return {
        "status": "healthy",
        "deterministic_engine": "online",
        "non_ai_guarantee": True,
        "total_rules": len(loader.rules_by_id),
        "total_cids": len(loader.rules_by_cid),
        "providers": sorted(list(provider_counts.keys())),
        "rules_by_provider": provider_counts,
        "policies_count": len(policies),
        "mandates_count": len(mandates),
        "supported_operators": [
            "EQ", "NEQ", "GT", "LT", "CONTAINS", "NOT_CONTAINS",
            "IN", "NOT_IN", "CIDR_OPEN_WORLD", "IAM_AST_WILDCARD",
            "REGEX", "EXISTS"
        ],
    }


def _format_rule_public(rule: DeterministicRuleSpec) -> Dict[str, Any]:
    rule_id = rule.rule_id
    if rule_id.startswith("QUALYS-"):
        rule_id = "LR-" + rule_id[7:]
    return {
        "rule_id": rule_id,
        "cid": str(rule.cid or rule_id.split("-")[-1]),
        "title": rule.title,
        "provider": rule.provider.upper(),
        "service": rule.service.upper(),
        "criticality": rule.criticality.upper(),
        "execution_type": str(rule.execution_type.value if hasattr(rule.execution_type, "value") else rule.execution_type),
        "target_source": rule.target_source,
        "policies": rule.policies,
        "mandates": rule.mandates,
        "conditions_count": len(rule.conditions),
    }


MANDATE_ALIASES: Dict[str, List[str]] = {
    "cis benchmark": ["cis", "controls"],
    "cis controls": ["cis", "controls"],
    "cis": ["cis"],
    "nist csf": ["nist", "csf"],
    "pci-dss": ["pci", "dss"],
    "pci-dss v4.0": ["pci", "dss"],
    "pci": ["pci"],
    "iso 27001": ["iso", "27001"],
    "iso 27001:2022": ["iso", "27001"],
    "iso/iec 27001:2022": ["iso", "27001"],
    "hipaa": ["hipaa"],
    "hipaa security rule": ["hipaa"],
    "fedramp moderate": ["fedramp", "moderate"],
    "fedramp": ["fedramp"],
    "soc 2": ["soc", "2"],
    "gdpr": ["gdpr"],
    "cmmc": ["cmmc"],
    "cmmc 2.0": ["cmmc"],
    "sox": ["sarbanes"],
    "sarbanes-oxley": ["sarbanes"],
    "ccpa": ["california consumer privacy", "sb-1121"],
    "nis 2": ["nis 2", "2022/2555"],
}


def _matches_mandate(filter_val: str, rule_mandates: List[str]) -> bool:
    """Smart matching across formal framework titles, common aliases, and punctuation variants."""
    if not filter_val or filter_val.strip().lower() in ("all mandates", "all", ""):
        return True

    clean_filter = filter_val.strip().lower()

    # 1. Direct exact or substring match
    for m in rule_mandates:
        m_lower = m.lower()
        if clean_filter in m_lower:
            return True

    # 2. Check alias map
    if clean_filter in MANDATE_ALIASES:
        keywords = MANDATE_ALIASES[clean_filter]
        for m in rule_mandates:
            m_lower = m.lower()
            if all(kw in m_lower for kw in keywords):
                return True

    # 3. Punctuation-normalized keyword match (e.g. "pci-dss v4.0" -> ["pci", "dss", "v4"])
    clean_norm_words = [w for w in re.sub(r"[^\w\s]", " ", clean_filter).split() if len(w) > 1]
    if clean_norm_words:
        for m in rule_mandates:
            m_norm = re.sub(r"[^\w\s]", " ", m.lower())
            if all(w in m_norm for w in clean_norm_words):
                return True

    return False


@router.get("/catalogs/controls", summary="Browse Cloud Security & Compliance Rules Catalog")
def list_catalog_controls(
    response: Response,
    provider: Optional[str] = Query(None, description="Filter by cloud provider: AWS, AZURE, GCP, OCI"),
    service: Optional[str] = Query(None, description="Filter by service name: S3, RDS, IAM, etc."),
    criticality: Optional[str] = Query(None, description="Filter by criticality: CRITICAL, HIGH, MEDIUM, LOW"),
    mandate: Optional[str] = Query(None, description="Filter by compliance mandate (e.g. SOC 2, PCI-DSS)"),
    policy: Optional[str] = Query(None, description="Filter by policy name"),
    query: Optional[str] = Query(None, description="Search query matching CID, service, or rule title"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
) -> Dict[str, Any]:
    """
    Returns paginated, searchable cloud security and compliance rules.
    Rules are sanitized with LogRaven identifiers (zero external vendor references).
    Rule export is strictly disabled to protect proprietary platform intelligence.
    """
    engine = get_engine()
    loader = engine.loader
    all_rules = list(loader.rules_by_id.values())

    filtered = []
    q_lower = query.lower().strip() if isinstance(query, str) and query.strip() else None
    prov_upper = provider.upper().strip() if isinstance(provider, str) and provider.strip() else None
    svc_upper = service.upper().strip() if isinstance(service, str) and service.strip() else None
    crit_upper = criticality.upper().strip() if isinstance(criticality, str) and criticality.strip() else None
    mand_val = mandate.strip() if isinstance(mandate, str) and mandate.strip() else None
    pol_lower = policy.lower().strip() if isinstance(policy, str) and policy.strip() else None
    page_num = page if isinstance(page, int) and page >= 1 else 1
    limit_num = limit if isinstance(limit, int) and limit >= 1 else 50

    for r in all_rules:
        if prov_upper and r.provider.upper() != prov_upper:
            continue
        if svc_upper and r.service.upper() != svc_upper:
            continue
        if crit_upper and r.criticality.upper() != crit_upper:
            continue
        if mand_val and not _matches_mandate(mand_val, r.mandates):
            continue
        if pol_lower and not any(pol_lower in p.lower() for p in r.policies):
            continue
        if q_lower:
            cid_str = str(r.cid or "")
            if q_lower not in r.title.lower() and q_lower not in cid_str and q_lower not in r.service.lower():
                continue
        filtered.append(r)

    total_count = len(filtered)
    total_pages = max(1, (total_count + limit_num - 1) // limit_num) if total_count else 0
    start_idx = (page_num - 1) * limit_num
    page_items = filtered[start_idx : start_idx + limit_num]

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Total-Pages"] = str(total_pages)
    response.headers["X-Page"] = str(page_num)
    response.headers["X-Page-Size"] = str(limit_num)

    return {
        "items": [_format_rule_public(r) for r in page_items],
        "total": total_count,
        "page": page_num,
        "total_pages": total_pages,
        "limit": limit_num,
    }


@router.post("/evaluate/native", summary="Execute LogRaven Native Cloud Compliance Scan")
async def evaluate_native_cloud_compliance(
    request: NonAIEvalRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    LogRaven Native real-time cloud and compliance evaluation engine.
    Executes 100% deterministic asset verification in sub-milliseconds without external AI latency.
    Persists audit findings into PostgreSQL so results, reports, and history are instantly available.
    """
    eval_result = evaluate_non_ai(request)
    session_id = eval_result["session_id"]

    try:
        job_uuid = uuid.UUID(session_id)
    except ValueError:
        job_uuid = uuid.uuid4()
        session_id = str(job_uuid)
        eval_result["session_id"] = session_id

    try:
        user_id = current_user.id if current_user else None
        if user_id is None:
            first_user_res = await db.execute(select(User).limit(1))
            first_user = first_user_res.scalar_one_or_none()
            if first_user:
                user_id = first_user.id

        provider = request.provider.upper()
        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        today = date.today()
        framework_id = f"LOGRAVEN-CSPM-{provider}"

        audit_job = AuditJob(
            id=job_uuid,
            user_id=user_id,
            company_name=f"LogRaven Native {provider} Compliance Audit",
            role_arn=f"{provider.lower()}:native-engine",
            audit_start_date=today,
            audit_end_date=today,
            frameworks=[framework_id],
            status="complete",
            raw_evidence={"evaluated_at": now_dt.isoformat(), "provider": provider},
            sanitized_evidence={"provider": provider},
            evidence_signals=eval_result.get("controls", {}),
        )
        db.add(audit_job)
        await db.flush()

        audit_results_rows = []
        controls_dict = eval_result.get("controls", {})
        pass_count = 0
        fail_count = 0

        for cid, c in controls_dict.items():
            c_status = c.get("status", "FAIL")
            if c_status == "PASS":
                pass_count += 1
            else:
                fail_count += 1

            cid_val = str(c.get("cid", cid))
            audit_results_rows.append(
                AuditResult(
                    audit_job_id=job_uuid,
                    framework=framework_id,
                    control_id=f"LR-{provider}-CID-{cid_val}",
                    control_name=c.get("title") or "Compliance Benchmark Control",
                    status=c_status,
                    evidence_count=len(c.get("passed_resources", [])) + len(c.get("failing_resources", [])),
                    ai_description=f"Deterministic rule evaluation: {c.get('title')}",
                    raw_evidence_summary={
                        "category": c.get("service") or "Security",
                        "criticality": c.get("criticality") or "HIGH",
                        "failing_resources": c.get("failing_resources") or [],
                        "passed_resources": c.get("passed_resources") or [],
                        "gaps": [f"Violation of baseline control CID-{cid_val}"] if c_status != "PASS" else [],
                        "evidence_references": [
                            f"Service: {c.get('service') or provider}",
                            f"Provider: {provider}",
                            "Engine: LogRaven Deterministic Rule AST Evaluator",
                        ],
                        "remediation": f"Review and remediate non-compliant {c.get('service') or 'cloud'} assets to comply with baseline.",
                    },
                )
            )

        db.add_all(audit_results_rows)

        total_controls = pass_count + fail_count
        score_pct = round((pass_count / max(1, total_controls)) * 100.0, 2)
        snapshot = ComplianceSnapshot(
            audit_job_id=job_uuid,
            framework=framework_id,
            score_percent=score_pct,
            pass_count=pass_count,
            fail_count=fail_count,
            partial_count=0,
            suppressed_count=0,
            results=eval_result.get("controls"),
        )
        db.add(snapshot)
        await db.commit()
    except Exception as exc:
        logger.warning("Could not persist native audit to database: %s", exc, exc_info=True)
        await db.rollback()

    return eval_result


@router.post("/collect-and-evaluate/aws", summary="Collect AWS Estate via Boto3 and Evaluate Non-AI")
@limiter.limit("5/minute")
async def collect_and_evaluate_aws(
    request: Request,
    payload: CollectAndEvalAWSRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Initiates Boto3 state and log collection against live AWS APIs (IAM, EC2/VPC, S3, KMS, CloudTrail)
    and passes the snapshot into the Deterministic Compliance Grader.
    Requires authenticated user and applies rate limiting (5 req/min).
    """
    t0 = time.perf_counter()
    try:
        collector = AWSStateAndLogCollector(region_name=payload.region_name)
        resources_by_service = collector.collect_all_resources(services=payload.services)
        cloudtrail_events = collector.collect_cloudtrail_events(max_results=payload.max_cloudtrail_events)
    except Exception as exc:
        logger.error("Failed to collect AWS resources: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AWS collection failed: {str(exc)}",
        )

    grader = DeterministicComplianceGrader(loader=get_engine().loader)
    grading_results = grader.evaluate_all_without_ai(
        provider="AWS",
        resources_by_service=resources_by_service,
        cloudtrail_events=cloudtrail_events,
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "status": "success",
        "non_ai_guarantee": True,
        "region_name": payload.region_name,
        "execution_summary": {
            "total_controls_evaluated": grading_results["total_controls_evaluated"],
            "controls_passed": grading_results["controls_passed"],
            "controls_failed": grading_results["controls_failed"],
            "latency_ms": elapsed_ms,
        },
        "policies": grading_results["policies"],
        "mandates": grading_results["mandates"],
        "controls": grading_results["controls"],
    }
