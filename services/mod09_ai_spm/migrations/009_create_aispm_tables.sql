-- Migration 009: Create AI-SPM Model Inventory and MCP Server Governance Tables (PRD-MOD-09)

CREATE TABLE IF NOT EXISTS ai_model_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_urn VARCHAR(512) NOT NULL,
    tenant_id UUID,
    provider VARCHAR(32) NOT NULL,              -- aws_bedrock, sagemaker, azure_openai, vertex_ai, huggingface
    model_name VARCHAR(128) NOT NULL,
    model_version VARCHAR(64),
    weight_format VARCHAR(32) NOT NULL,         -- safetensors | pickle | onnx | gguf
    has_unsafe_deserialization BOOLEAN NOT NULL DEFAULT FALSE,
    guardrails_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    prompt_logging_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    scanned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_model_urn ON ai_model_inventory(asset_urn);
CREATE INDEX IF NOT EXISTS idx_ai_model_unsafe ON ai_model_inventory(has_unsafe_deserialization);

CREATE TABLE IF NOT EXISTS mcp_server_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    server_urn VARCHAR(512) NOT NULL,
    endpoint_url TEXT NOT NULL,
    is_publicly_exposed BOOLEAN NOT NULL DEFAULT FALSE,
    auth_enforced BOOLEAN NOT NULL DEFAULT FALSE,
    available_tools JSONB NOT NULL DEFAULT '[]'::jsonb, -- Array of tool definitions & permissions
    has_high_risk_tools BOOLEAN NOT NULL DEFAULT FALSE, -- Grants shell execution or arbitrary SQL
    last_audited_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mcp_server_urn ON mcp_server_inventory(server_urn);
CREATE INDEX IF NOT EXISTS idx_mcp_server_risk ON mcp_server_inventory(is_publicly_exposed, has_high_risk_tools);
