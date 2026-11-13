-- migrations/002_create_cspm_assets.sql
-- Module 02: Agentless API Crawler & Canonical URN Asset Normalizer

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS cspm_assets (
    urn VARCHAR(512) PRIMARY KEY,
    tenant_id UUID NOT NULL,
    account_id VARCHAR(128) NOT NULL,
    provider VARCHAR(16) NOT NULL CHECK (provider IN ('aws','azure','gcp','oci','alibaba','k8s','saas')),
    region VARCHAR(64) NOT NULL,
    service VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(256) NOT NULL,
    resource_name VARCHAR(256),
    config_json JSONB NOT NULL,
    config_sha256 CHAR(64) NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cspm_assets_tenant_provider ON cspm_assets(tenant_id, provider);
CREATE INDEX IF NOT EXISTS idx_cspm_assets_config_sha ON cspm_assets(config_sha256);
CREATE INDEX IF NOT EXISTS idx_cspm_assets_last_seen ON cspm_assets(last_seen_at) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_cspm_assets_tenant_service ON cspm_assets(tenant_id, service);

