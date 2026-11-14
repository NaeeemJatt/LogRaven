"""Module 11: ASPM, IaC AST Scanner, & Code-to-Cloud GitOps Auto-PR Engine.

FastAPI Router and GitOps Remediation Coordinator (PRD-MOD-11).
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from services.mod11_iac_gitops.internal.cloudbots.emergency_bots import (
    CloudBotEnableKMSRotation,
    CloudBotS3BlockPublic,
    CloudBotSGRevokeSSH,
)
from services.mod11_iac_gitops.internal.lineage_tracker.fuzzy_ast_matcher import FuzzyASTMatcher
from services.mod11_iac_gitops.internal.lineage_tracker.tag_correlator import TagCorrelator
from services.mod11_iac_gitops.internal.pr_generator.ast_patcher import ASTPatcher
from services.mod11_iac_gitops.internal.pr_generator.github_client import GitHubPRClient
from services.mod11_iac_gitops.internal.repository.iac_repo import IaCRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Module 11: ASPM & GitOps Auto-PR"])


# ── Request / Response Models ─────────────────────────────────────────────

class PatchHCLRequest(BaseModel):
    hcl_content: str
    attribute: str
    new_value: Any
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None


class CorrelateLineageRequest(BaseModel):
    asset_urn: str
    tags: Dict[str, Any] = Field(default_factory=dict)
    file_content: Optional[str] = None
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None


class CreateRemediationPRRequest(BaseModel):
    repo_full_name: str
    base_branch: str = "main"
    rule_id: str
    file_path: str
    diff_text: str
    finding_id: Optional[uuid.UUID] = None
    finding_title: str = "Automated Security Remediation"
    pr_number: Optional[int] = None


class RegisterRepoRequest(BaseModel):
    provider: str = "github"
    repo_full_name: str
    installation_id: str
    default_branch: str = "main"


class CloudBotActionRequest(BaseModel):
    bot_id: str  # bot-s3-block-public, bot-sg-revoke-ssh, bot-enable-kms-rotation
    target_resource: str


# ── REST API Endpoints ───────────────────────────────────────────────────

@router.post("/patch")
async def patch_iac_content(
    req: PatchHCLRequest,
    current_user: User = Depends(get_current_user),
):
    """Surgically modifies Terraform HCL source text, preserving comments and formatting."""
    return ASTPatcher.patch_attribute(
        hcl_content=req.hcl_content,
        attribute=req.attribute,
        new_value=req.new_value,
        resource_type=req.resource_type,
        resource_name=req.resource_name,
    )


@router.post("/lineage/correlate")
async def correlate_code_to_cloud(
    req: CorrelateLineageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Correlates runtime cloud asset URN and tags back to source Git repository, file, and line number."""
    meta = TagCorrelator.extract_git_metadata(req.tags)

    start_line = meta.get("line_number") or 1
    end_line = start_line

    if req.file_content and req.resource_type:
        s_line, e_line = FuzzyASTMatcher.locate_resource(
            file_content=req.file_content,
            resource_type=req.resource_type,
            resource_name=req.resource_name,
        )
        if s_line != -1:
            start_line = s_line
            end_line = e_line

    repo_record = None
    if meta.get("repo_full_name"):
        repo_record = await IaCRepository.get_repo_by_name(db, meta["repo_full_name"])
        if repo_record:
            await IaCRepository.record_lineage(
                session=db,
                asset_urn=req.asset_urn,
                repo_id=repo_record.id,
                file_path=meta.get("file_path") or "main.tf",
                start_line=start_line,
                end_line=end_line,
                resource_block_name=f"{req.resource_type or 'resource'}.{req.resource_name or 'main'}",
                commit_sha=meta.get("commit_sha") or "HEAD",
            )
            await db.commit()

    return {
        "asset_urn": req.asset_urn,
        "has_lineage": meta["has_lineage"],
        "repo_full_name": meta.get("repo_full_name"),
        "file_path": meta.get("file_path"),
        "line_number": start_line,
        "start_line": start_line,
        "end_line": end_line,
        "commit_sha": meta.get("commit_sha"),
        "repo_registered": repo_record is not None,
    }


@router.post("/remediate/pr")
async def create_gitops_pr(
    req: CreateRemediationPRRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates an automated GitOps Pull Request on GitHub/GitLab with surgical AST patch."""
    pr_result = GitHubPRClient.create_remediation_pr(
        repo_full_name=req.repo_full_name,
        base_branch=req.base_branch,
        rule_id=req.rule_id,
        file_path=req.file_path,
        diff_text=req.diff_text,
        finding_title=req.finding_title,
        pr_number=req.pr_number,
    )

    # Persist in DB if repo is registered
    repo = await IaCRepository.get_repo_by_name(db, req.repo_full_name)
    if not repo:
        tenant_id = getattr(current_user, "tenant_id", None)
        repo = await IaCRepository.register_repository(
            session=db,
            provider="github",
            repo_full_name=req.repo_full_name,
            installation_id="mock-inst-123",
            default_branch=req.base_branch,
            tenant_id=tenant_id,
        )

    user_id = getattr(current_user, "id", None)
    tenant_id = getattr(current_user, "tenant_id", None)
    await IaCRepository.record_remediation_pr(
        session=db,
        repo_id=repo.id,
        pr_number=pr_result["pr_number"],
        pr_url=pr_result["pr_url"],
        branch_name=pr_result["branch_name"],
        finding_id=req.finding_id,
        created_by_user_id=user_id,
        tenant_id=tenant_id,
    )
    await db.commit()

    return pr_result


@router.post("/repos")
async def register_repository(
    req: RegisterRepoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers a connected Git repository for automated Pull Requests."""
    tenant_id = getattr(current_user, "tenant_id", None)
    repo = await IaCRepository.register_repository(
        session=db,
        provider=req.provider,
        repo_full_name=req.repo_full_name,
        installation_id=req.installation_id,
        default_branch=req.default_branch,
        tenant_id=tenant_id,
    )
    await db.commit()
    return {
        "id": str(repo.id),
        "provider": repo.provider,
        "repo_full_name": repo.repo_full_name,
        "default_branch": repo.default_branch,
        "is_active": repo.is_active,
    }


@router.get("/repos")
async def list_repositories(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists connected Git repositories."""
    repos = await IaCRepository.list_repositories(db, limit=limit, offset=offset)
    return {
        "total": len(repos),
        "repositories": [
            {
                "id": str(r.id),
                "provider": r.provider,
                "repo_full_name": r.repo_full_name,
                "default_branch": r.default_branch,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in repos
        ],
    }


@router.get("/prs")
async def list_remediation_prs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists submitted GitOps Pull Requests."""
    prs = await IaCRepository.list_prs(db, limit=limit, offset=offset)
    return {
        "total": len(prs),
        "prs": [
            {
                "id": str(p.id),
                "repo_id": str(p.repo_id),
                "pr_number": p.pr_number,
                "pr_url": p.pr_url,
                "branch_name": p.branch_name,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in prs
        ],
    }


@router.post("/cloudbots/action")
async def execute_cloudbot(
    req: CloudBotActionRequest,
    current_user: User = Depends(get_current_user),
):
    """Generates an emergency serverless remediation action from CloudBots."""
    if req.bot_id == "bot-s3-block-public":
        return CloudBotS3BlockPublic.generate_remediation_action(req.target_resource)
    elif req.bot_id == "bot-sg-revoke-ssh":
        return CloudBotSGRevokeSSH.generate_remediation_action(req.target_resource)
    elif req.bot_id == "bot-enable-kms-rotation":
        return CloudBotEnableKMSRotation.generate_remediation_action(req.target_resource)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown CloudBot ID: {req.bot_id}")
