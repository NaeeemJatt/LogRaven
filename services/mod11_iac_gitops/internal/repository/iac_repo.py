"""Repository for Module 11: ASPM & GitOps Auto-PR (PRD-MOD-11)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod11_iac_gitops.internal.repository.models import GitOpsRemediationPR, GitRepository, IaCLineageRecord


class IaCRepository:
    """Persistence operations for Git repositories, code-to-cloud lineages, and GitOps PRs."""

    @staticmethod
    async def register_repository(
        session: AsyncSession,
        provider: str,
        repo_full_name: str,
        installation_id: str,
        default_branch: str = "main",
        tenant_id: Optional[uuid.UUID] = None,
    ) -> GitRepository:
        """Upserts a connected Git repository."""
        query = select(GitRepository).where(
            GitRepository.provider == provider,
            GitRepository.repo_full_name == repo_full_name,
        )
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.installation_id = installation_id
            existing.default_branch = default_branch
            existing.is_active = True
            await session.flush()
            return existing
        else:
            record = GitRepository(
                tenant_id=tenant_id,
                provider=provider,
                repo_full_name=repo_full_name,
                installation_id=installation_id,
                default_branch=default_branch,
                is_active=True,
            )
            session.add(record)
            await session.flush()
            return record

    @staticmethod
    async def record_lineage(
        session: AsyncSession,
        asset_urn: str,
        repo_id: uuid.UUID,
        file_path: str,
        start_line: int,
        end_line: int,
        resource_block_name: str,
        commit_sha: str,
    ) -> IaCLineageRecord:
        """Upserts a code-to-cloud lineage record."""
        now = datetime.now(timezone.utc)
        query = select(IaCLineageRecord).where(
            IaCLineageRecord.asset_urn == asset_urn,
            IaCLineageRecord.repo_id == repo_id,
        )
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.file_path = file_path
            existing.start_line = start_line
            existing.end_line = end_line
            existing.resource_block_name = resource_block_name
            existing.commit_sha = commit_sha
            existing.last_verified_at = now
            await session.flush()
            return existing
        else:
            record = IaCLineageRecord(
                asset_urn=asset_urn,
                repo_id=repo_id,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                resource_block_name=resource_block_name,
                commit_sha=commit_sha,
                last_verified_at=now,
            )
            session.add(record)
            await session.flush()
            return record

    @staticmethod
    async def record_remediation_pr(
        session: AsyncSession,
        repo_id: uuid.UUID,
        pr_number: int,
        pr_url: str,
        branch_name: str,
        finding_id: Optional[uuid.UUID] = None,
        created_by_user_id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> GitOpsRemediationPR:
        """Records an automated GitOps Pull Request."""
        record = GitOpsRemediationPR(
            tenant_id=tenant_id,
            finding_id=finding_id,
            repo_id=repo_id,
            pr_number=pr_number,
            pr_url=pr_url,
            branch_name=branch_name,
            status="OPEN",
            created_by_user_id=created_by_user_id,
        )
        session.add(record)
        await session.flush()
        return record

    @staticmethod
    async def get_repo_by_name(
        session: AsyncSession,
        repo_full_name: str,
    ) -> Optional[GitRepository]:
        """Finds repository by owner/repo name."""
        query = select(GitRepository).where(GitRepository.repo_full_name == repo_full_name)
        res = await session.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def list_repositories(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[GitRepository]:
        """Lists connected repositories."""
        query = select(GitRepository).order_by(desc(GitRepository.created_at)).limit(limit).offset(offset)
        res = await session.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def list_prs(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[GitOpsRemediationPR]:
        """Lists GitOps PRs."""
        query = select(GitOpsRemediationPR).order_by(desc(GitOpsRemediationPR.created_at)).limit(limit).offset(offset)
        res = await session.execute(query)
        return list(res.scalars().all())
