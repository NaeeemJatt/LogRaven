"""SQLAlchemy ORM models for AI-SPM Model Inventory & MCP Governance (PRD-MOD-09)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AIModelInventory(Base):
    __tablename__ = "ai_model_inventory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # aws_bedrock, sagemaker, azure_openai, vertex_ai
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    weight_format: Mapped[str] = mapped_column(String(32), nullable=False, default="safetensors")  # safetensors | pickle | onnx | gguf
    has_unsafe_deserialization: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    guardrails_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prompt_logging_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class MCPServerInventory(Base):
    __tablename__ = "mcp_server_inventory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    server_urn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    endpoint_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_publicly_exposed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auth_enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    available_tools: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    has_high_risk_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    last_audited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
