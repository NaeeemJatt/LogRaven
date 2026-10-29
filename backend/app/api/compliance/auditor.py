"""API routes for external CPA Auditor Portal and Cryptographic Evidence Vault."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.compliance.vault import build_evidence_vault_zip
from app.dependencies import get_current_user, get_db
from app.models.soc2_audit import AuditJob, AuditorAccessToken, ComplianceException
from app.limiter import limiter
from app.utils.audit import add_audit
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/compliance/auditor", tags=["compliance-auditor"])


def _hash_string(val: str) -> str:
    return hashlib.sha256(val.strip().encode("utf-8")).hexdigest()


# ── Pydantic Request & Response Schemas ────────────────────────────────────────

class CreateAuditorTokenRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    cloud_account_id: uuid.UUID | None = None
    recipient_name: str | None = Field(default=None, max_length=255)
    recipient_email: str | None = Field(default=None, max_length=255)
    passcode: str | None = Field(default=None, min_length=4, max_length=64)
    duration_days: int = Field(default=30, ge=1, le=180)
    allowed_frameworks: list[str] = Field(default_factory=lambda: ["soc2", "iso27001"])
    can_download_raw_evidence: bool = True


class AuditorTokenCreatedResponse(BaseModel):
    id: str
    token: str
    company_name: str
    recipient_name: str | None
    recipient_email: str | None
    allowed_frameworks: list[str]
    can_download_raw_evidence: bool
    expires_at: str
    created_at: str


class AuditorTokenListItem(BaseModel):
    id: str
    company_name: str
    recipient_name: str | None
    recipient_email: str | None
    allowed_frameworks: list[str]
    can_download_raw_evidence: bool
    expires_at: str
    is_expired: bool
    is_revoked: bool
    access_count: int
    last_accessed_at: str | None
    created_at: str


class VerifyTokenRequest(BaseModel):
    token: str = Field(..., min_length=16)
    passcode: str | None = None


class AuditorPortalOverview(BaseModel):
    company_name: str
    recipient_name: str | None
    expires_at: str
    allowed_frameworks: list[str]
    can_download_raw_evidence: bool
    latest_audit: dict | None
    recent_audits: list[dict]
    active_exceptions_count: int


# ── Helper: Validate Auditor Token ───────────────────────────────────────────

async def _get_valid_token(
    db: AsyncSession,
    raw_token: str | None = None,
    passcode: str | None = None,
    authorization: str | None = None,
    x_auditor_token: str | None = None,
    track_access: bool = False,
) -> AuditorAccessToken:
    effective_token = None
    if isinstance(x_auditor_token, str) and x_auditor_token.strip():
        effective_token = x_auditor_token.strip()
    elif isinstance(authorization, str) and authorization.strip().startswith("Bearer "):
        bearer_val = authorization.strip()[7:].strip()
        if bearer_val:
            effective_token = bearer_val
    elif isinstance(raw_token, str) and raw_token.strip():
        effective_token = raw_token.strip()

    if not effective_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Auditor access token required via Authorization header, X-Auditor-Token, or path parameter.",
        )

    token_hash = _hash_string(effective_token)
    stmt = select(AuditorAccessToken).where(AuditorAccessToken.token_hash == token_hash)
    res = await db.execute(stmt)
    token_record = res.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auditor access link is invalid or does not exist.",
        )

    if token_record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This auditor access link has been revoked by the account administrator.",
        )

    now = datetime.now(timezone.utc)
    if token_record.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This auditor access link has expired. Please request a new link.",
        )

    if token_record.passcode_hash:
        if not passcode or not secrets.compare_digest(_hash_string(passcode), token_record.passcode_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid passcode required to access this auditor vault.",
            )

    if track_access:
        token_record.access_count = (token_record.access_count or 0) + 1
        token_record.last_accessed_at = now
        await db.commit()

    return token_record


# ── Authenticated User Endpoints ──────────────────────────────────────────────

@router.post("/tokens", response_model=AuditorTokenCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_auditor_token(
    body: CreateAuditorTokenRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new time-bound, read-only auditor link for external CPAs."""
    plain_token = secrets.token_urlsafe(32)
    token_hash = _hash_string(plain_token)
    passcode_hash = _hash_string(body.passcode) if body.passcode else None

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=body.duration_days)

    token_record = AuditorAccessToken(
        id=uuid.uuid4(),
        user_id=current_user.id,
        company_name=body.company_name.strip(),
        cloud_account_id=body.cloud_account_id,
        token_hash=token_hash,
        passcode_hash=passcode_hash,
        recipient_name=body.recipient_name.strip() if body.recipient_name else None,
        recipient_email=body.recipient_email.strip().lower() if body.recipient_email else None,
        allowed_frameworks=body.allowed_frameworks,
        can_download_raw_evidence=body.can_download_raw_evidence,
        expires_at=expires_at,
        access_count=0,
        created_at=now,
    )
    db.add(token_record)
    await db.flush()

    add_audit(
        db,
        user_id=current_user.id,
        action="create_auditor_token",
        request=request,
        metadata={
            "token_id": str(token_record.id),
            "company_name": token_record.company_name,
            "recipient_email": token_record.recipient_email,
            "expires_at": expires_at.isoformat(),
        },
    )
    await db.commit()
    await db.refresh(token_record)

    return AuditorTokenCreatedResponse(
        id=str(token_record.id),
        token=plain_token,
        company_name=token_record.company_name,
        recipient_name=token_record.recipient_name,
        recipient_email=token_record.recipient_email,
        allowed_frameworks=token_record.allowed_frameworks,
        can_download_raw_evidence=token_record.can_download_raw_evidence,
        expires_at=token_record.expires_at.isoformat(),
        created_at=token_record.created_at.isoformat(),
    )


@router.get("/tokens", response_model=list[AuditorTokenListItem])
async def list_auditor_tokens(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all auditor access tokens created by the current user."""
    stmt = (
        select(AuditorAccessToken)
        .where(AuditorAccessToken.user_id == current_user.id)
        .order_by(desc(AuditorAccessToken.created_at))
    )
    res = await db.execute(stmt)
    tokens = res.scalars().all()

    now = datetime.now(timezone.utc)
    return [
        AuditorTokenListItem(
            id=str(t.id),
            company_name=t.company_name,
            recipient_name=t.recipient_name,
            recipient_email=t.recipient_email,
            allowed_frameworks=t.allowed_frameworks,
            can_download_raw_evidence=t.can_download_raw_evidence,
            expires_at=t.expires_at.isoformat(),
            is_expired=t.expires_at < now,
            is_revoked=t.revoked_at is not None,
            access_count=t.access_count or 0,
            last_accessed_at=t.last_accessed_at.isoformat() if t.last_accessed_at else None,
            created_at=t.created_at.isoformat(),
        )
        for t in tokens
    ]


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_auditor_token(
    token_id: uuid.UUID,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Immediately revoke an auditor access token."""
    stmt = select(AuditorAccessToken).where(
        AuditorAccessToken.id == token_id,
        AuditorAccessToken.user_id == current_user.id,
    )
    res = await db.execute(stmt)
    token_record = res.scalar_one_or_none()

    if not token_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auditor token not found.")

    token_record.revoked_at = datetime.now(timezone.utc)
    add_audit(
        db,
        user_id=current_user.id,
        action="revoke_auditor_token",
        request=request,
        metadata={"token_id": str(token_record.id), "company_name": token_record.company_name},
    )
    await db.commit()


# ── Public / Auditor Portal Endpoints (Token Authenticated) ───────────────────

@router.post("/portal/verify")
@limiter.limit("5/minute")
async def verify_auditor_token(
    request: Request,
    body: VerifyTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate token and passcode before rendering the Auditor Room."""
    token_record = await _get_valid_token(db, body.token, passcode=body.passcode, track_access=True)
    return {
        "valid": True,
        "company_name": token_record.company_name,
        "recipient_name": token_record.recipient_name,
        "expires_at": token_record.expires_at.isoformat(),
        "allowed_frameworks": token_record.allowed_frameworks,
        "can_download_raw_evidence": token_record.can_download_raw_evidence,
    }


@router.get("/portal/overview", response_model=AuditorPortalOverview)
@router.get("/portal/{token}/overview", response_model=AuditorPortalOverview)
async def get_auditor_portal_overview(
    token: str | None = None,
    passcode: str | None = None,
    authorization: str | None = Header(None),
    x_auditor_token: str | None = Header(None, alias="X-Auditor-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve compliance overview and audit timeline for external auditors."""
    token_record = await _get_valid_token(
        db,
        raw_token=token,
        passcode=passcode,
        authorization=authorization,
        x_auditor_token=x_auditor_token,
        track_access=False,
    )

    # Fetch audit jobs for this company and tenant
    stmt = (
        select(AuditJob)
        .options(selectinload(AuditJob.results), selectinload(AuditJob.snapshots))
        .where(
            AuditJob.user_id == token_record.user_id,
            AuditJob.company_name == token_record.company_name,
            AuditJob.status == "complete",
        )
        .order_by(desc(AuditJob.created_at))
        .limit(10)
    )
    res = await db.execute(stmt)
    jobs = res.scalars().all()

    def _calc_job_score(j: AuditJob) -> float:
        if getattr(j, "snapshots", None) and len(j.snapshots) > 0:
            return round(float(sum(s.score_percent for s in j.snapshots) / len(j.snapshots)), 1)
        results = getattr(j, "results", None) or []
        if not results:
            return 0.0
        passed = sum(1 for r in results if r.status == "PASS")
        return round(float((passed / len(results)) * 100), 1)

    # Active business exceptions
    exc_stmt = select(ComplianceException).where(
        ComplianceException.user_id == token_record.user_id,
        ComplianceException.company_name == token_record.company_name,
        func.lower(ComplianceException.status) == "active",
    )
    exc_res = await db.execute(exc_stmt)
    exceptions = exc_res.scalars().all()

    latest_dict = None
    if jobs:
        latest = jobs[0]
        results_list = latest.results or []
        job_score = _calc_job_score(latest)
        latest_dict = {
            "audit_id": str(latest.id),
            "score_percent": job_score,
            "raw_score_percent": job_score,
            "frameworks": latest.frameworks,
            "completed_at": (getattr(latest, "completed_at", None) or getattr(latest, "created_at", None)).isoformat()
            if (getattr(latest, "completed_at", None) or getattr(latest, "created_at", None))
            else None,
            "controls_passed": sum(1 for r in results_list if r.status == "PASS"),
            "controls_failed": sum(1 for r in results_list if r.status == "FAIL"),
            "controls_partial": sum(1 for r in results_list if r.status == "PARTIAL"),
            "controls_suppressed": sum(1 for r in results_list if getattr(r, "status", None) == "SUPPRESSED"),
            "total_controls": len(results_list),
        }

    recent_audits = [
        {
            "audit_id": str(j.id),
            "score_percent": _calc_job_score(j),
            "raw_score_percent": _calc_job_score(j),
            "frameworks": j.frameworks,
            "completed_at": (getattr(j, "completed_at", None) or getattr(j, "created_at", None)).isoformat()
            if (getattr(j, "completed_at", None) or getattr(j, "created_at", None))
            else None,
        }
        for j in jobs
    ]

    return AuditorPortalOverview(
        company_name=token_record.company_name,
        recipient_name=token_record.recipient_name,
        expires_at=token_record.expires_at.isoformat(),
        allowed_frameworks=token_record.allowed_frameworks,
        can_download_raw_evidence=token_record.can_download_raw_evidence,
        latest_audit=latest_dict,
        recent_audits=recent_audits,
        active_exceptions_count=len(exceptions),
    )


@router.get("/portal/exceptions")
@router.get("/portal/{token}/exceptions")
async def get_auditor_portal_exceptions(
    token: str | None = None,
    passcode: str | None = None,
    authorization: str | None = Header(None),
    x_auditor_token: str | None = Header(None, alias="X-Auditor-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full business logic exception ledger for auditor review."""
    token_record = await _get_valid_token(
        db,
        raw_token=token,
        passcode=passcode,
        authorization=authorization,
        x_auditor_token=x_auditor_token,
        track_access=False,
    )

    stmt = (
        select(ComplianceException)
        .where(
            ComplianceException.user_id == token_record.user_id,
            ComplianceException.company_name == token_record.company_name,
            func.lower(ComplianceException.status) == "active",
        )
        .order_by(ComplianceException.control_id)
    )
    res = await db.execute(stmt)
    exceptions = res.scalars().all()

    return [
        {
            "id": str(e.id),
            "control_id": e.control_id,
            "framework": e.framework,
            "status": e.status,
            "justification": getattr(e, "business_justification", None) or getattr(e, "justification", ""),
            "compensating_controls": e.compensating_controls,
            "authorized_by": getattr(e, "suppressed_by", None) or getattr(e, "authorized_by", ""),
            "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in exceptions
    ]


@router.get("/portal/evidence-vault")
@router.get("/portal/{token}/evidence-vault")
async def download_auditor_evidence_vault(
    token: str | None = None,
    passcode: str | None = None,
    authorization: str | None = Header(None),
    x_auditor_token: str | None = Header(None, alias="X-Auditor-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Download cryptographically hashed Evidence Vault ZIP archive."""
    token_record = await _get_valid_token(
        db,
        raw_token=token,
        passcode=passcode,
        authorization=authorization,
        x_auditor_token=x_auditor_token,
        track_access=True,
    )

    if not token_record.can_download_raw_evidence:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Evidence download permission has not been granted for this auditor link.",
        )

    # Fetch audit jobs
    stmt = (
        select(AuditJob)
        .options(selectinload(AuditJob.results), selectinload(AuditJob.snapshots))
        .where(
            AuditJob.user_id == token_record.user_id,
            AuditJob.company_name == token_record.company_name,
            AuditJob.status == "complete",
        )
        .order_by(desc(AuditJob.created_at))
        .limit(5)
    )
    res = await db.execute(stmt)
    jobs = list(res.scalars().all())

    # Fetch exceptions
    exc_stmt = select(ComplianceException).where(
        ComplianceException.user_id == token_record.user_id,
        ComplianceException.company_name == token_record.company_name,
        func.lower(ComplianceException.status) == "active",
    )
    exc_res = await db.execute(exc_stmt)
    exceptions = list(exc_res.scalars().all())

    zip_bytes, zip_filename = build_evidence_vault_zip(
        company_name=token_record.company_name,
        audit_jobs=jobs,
        exceptions=exceptions,
        allowed_frameworks=token_record.allowed_frameworks,
        include_raw_telemetry=True,
    )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate",
        },
    )
