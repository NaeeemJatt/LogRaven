"""Repository for AI-SPM Model Inventory & MCP Governance (PRD-MOD-09)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.mod09_ai_spm.internal.repository.models import AIModelInventory, MCPServerInventory


class AISPMRepository:
    """Persistence operations for AI models, weights, and MCP servers."""

    @staticmethod
    async def record_ai_model(
        session: AsyncSession,
        asset_urn: str,
        provider: str,
        model_name: str,
        weight_format: str,
        has_unsafe_deserialization: bool,
        guardrails_enabled: bool,
        prompt_logging_enabled: bool,
        model_version: Optional[str] = None,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> AIModelInventory:
        """Upserts an AI model into the AI-BOM."""
        now = datetime.now(timezone.utc)
        query = select(AIModelInventory).where(AIModelInventory.asset_urn == asset_urn)
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.provider = provider
            existing.model_name = model_name
            existing.model_version = model_version
            existing.weight_format = weight_format
            existing.has_unsafe_deserialization = has_unsafe_deserialization
            existing.guardrails_enabled = guardrails_enabled
            existing.prompt_logging_enabled = prompt_logging_enabled
            existing.scanned_at = now
            await session.flush()
            return existing
        else:
            record = AIModelInventory(
                tenant_id=tenant_id,
                asset_urn=asset_urn,
                provider=provider,
                model_name=model_name,
                model_version=model_version,
                weight_format=weight_format,
                has_unsafe_deserialization=has_unsafe_deserialization,
                guardrails_enabled=guardrails_enabled,
                prompt_logging_enabled=prompt_logging_enabled,
                scanned_at=now,
            )
            session.add(record)
            await session.flush()
            return record

    @staticmethod
    async def record_mcp_server(
        session: AsyncSession,
        server_urn: str,
        endpoint_url: str,
        is_publicly_exposed: bool,
        auth_enforced: bool,
        available_tools: List[Dict[str, Any]],
        has_high_risk_tools: bool,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> MCPServerInventory:
        """Upserts an MCP server record and its tool capabilities."""
        now = datetime.now(timezone.utc)
        query = select(MCPServerInventory).where(MCPServerInventory.server_urn == server_urn)
        res = await session.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            existing.endpoint_url = endpoint_url
            existing.is_publicly_exposed = is_publicly_exposed
            existing.auth_enforced = auth_enforced
            existing.available_tools = available_tools
            existing.has_high_risk_tools = has_high_risk_tools
            existing.last_audited_at = now
            await session.flush()
            return existing
        else:
            record = MCPServerInventory(
                tenant_id=tenant_id,
                server_urn=server_urn,
                endpoint_url=endpoint_url,
                is_publicly_exposed=is_publicly_exposed,
                auth_enforced=auth_enforced,
                available_tools=available_tools,
                has_high_risk_tools=has_high_risk_tools,
                last_audited_at=now,
            )
            session.add(record)
            await session.flush()
            return record

    @staticmethod
    async def list_models(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AIModelInventory]:
        """Lists cataloged AI models."""
        query = select(AIModelInventory).order_by(desc(AIModelInventory.scanned_at)).limit(limit).offset(offset)
        res = await session.execute(query)
        return list(res.scalars().all())

    @staticmethod
    async def list_mcp_servers(
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MCPServerInventory]:
        """Lists cataloged MCP servers."""
        query = select(MCPServerInventory).order_by(desc(MCPServerInventory.last_audited_at)).limit(limit).offset(offset)
        res = await session.execute(query)
        return list(res.scalars().all())
