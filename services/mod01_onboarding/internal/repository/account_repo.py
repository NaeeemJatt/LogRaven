"""Account repository layer for CloudAccountV2."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod01_onboarding.internal.repository.models import CloudAccountV2
from services.mod01_onboarding.internal.crypto import generate_external_id, encrypt_external_id, decrypt_external_id


class AccountRepository:
    """Async repository for CloudAccountV2 CRUD with transparent ExternalId encryption."""

    @staticmethod
    async def create_account(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider: str,
        native_account_id: str,
        role_arn_or_sp: str,
        external_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        event_stream_arn: Optional[str] = None,
        cloud_group_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[CloudAccountV2, str]:
        """Create cloud account with encrypted external_id.
        
        Returns tuple of (created_entity, plaintext_external_id).
        """
        plain_ext_id = external_id or generate_external_id()
        encrypted_ext_id = encrypt_external_id(plain_ext_id)

        account = CloudAccountV2(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider=provider.lower().strip(),
            native_account_id=str(native_account_id).strip(),
            organization_id=organization_id.strip() if organization_id else None,
            role_arn_or_sp=role_arn_or_sp.strip(),
            external_id_enc=encrypted_ext_id,
            event_stream_arn=event_stream_arn.strip() if event_stream_arn else None,
            status="PENDING_VALIDATION",
            missing_permissions=[],
            cloud_group_ids=[str(g) for g in (cloud_group_ids or [])],
        )
        session.add(account)
        await session.flush()
        return account, plain_ext_id

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        account_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> Optional[CloudAccountV2]:
        """Fetch account by ID with optional tenant scope enforcement."""
        query = select(CloudAccountV2).where(CloudAccountV2.id == account_id)
        if tenant_id:
            query = query.where(CloudAccountV2.tenant_id == tenant_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_native_id(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider: str,
        native_account_id: str,
    ) -> Optional[CloudAccountV2]:
        """Fetch account by tenant_id, provider, and native_account_id."""
        query = select(CloudAccountV2).where(
            CloudAccountV2.tenant_id == tenant_id,
            CloudAccountV2.provider == provider.lower().strip(),
            CloudAccountV2.native_account_id == str(native_account_id).strip(),
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    def get_plaintext_external_id(account: CloudAccountV2) -> str:
        """Decrypt account external_id_enc."""
        return decrypt_external_id(account.external_id_enc)

    @staticmethod
    async def update_status(
        session: AsyncSession,
        account_id: uuid.UUID,
        status: str,
        missing_permissions: Optional[List[str]] = None,
        event_stream_arn: Optional[str] = None,
    ) -> Optional[CloudAccountV2]:
        """Update account status and health inspection metadata."""
        account = await AccountRepository.get_by_id(session, account_id)
        if not account:
            return None
        account.status = status
        account.missing_permissions = missing_permissions or []
        if event_stream_arn is not None:
            account.event_stream_arn = event_stream_arn
        account.last_verified_at = datetime.now(timezone.utc)
        account.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return account

    @staticmethod
    async def list_accounts(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        provider: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CloudAccountV2]:
        """List cloud accounts for tenant."""
        query = select(CloudAccountV2).where(CloudAccountV2.tenant_id == tenant_id)
        if provider:
            query = query.where(CloudAccountV2.provider == provider.lower().strip())
        query = query.order_by(CloudAccountV2.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())

