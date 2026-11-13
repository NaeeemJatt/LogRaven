-- migrations/001_create_cloud_accounts.sql
-- Module 01: Multi-Cloud Onboarding & Cross-Account Trust Broker

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS cloud_accounts_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    provider VARCHAR(16) NOT NULL CHECK (provider IN ('aws','azure','gcp','oci','alibaba','k8s','saas')),
    native_account_id VARCHAR(128) NOT NULL, -- 12-digit AWS ID, Azure Sub UUID, GCP Project ID
    organization_id VARCHAR(128),            -- AWS Org ID (o-xxx), Azure Tenant ID, GCP Org ID
    role_arn_or_sp TEXT NOT NULL,            -- arn:aws:iam::...:role/LogRavenCSPMReader
    external_id_enc BYTEA NOT NULL,          -- AES-256-GCM encrypted ExternalId
    event_stream_arn TEXT,                   -- EventBridge Bus ARN / Event Hub ID / PubSub Topic
    status VARCHAR(24) NOT NULL DEFAULT 'PENDING_VALIDATION', -- PENDING_VALIDATION | CONNECTED | DEGRADED | ERROR
    missing_permissions TEXT[] DEFAULT '{}',
    cloud_group_ids UUID[] DEFAULT '{}',
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, provider, native_account_id)
);

CREATE TABLE IF NOT EXISTS cloud_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(128) NOT NULL,
    business_impact VARCHAR(16) NOT NULL CHECK (business_impact IN ('critical', 'high', 'medium', 'low')),
    environment VARCHAR(16) NOT NULL CHECK (environment IN ('prod', 'staging', 'dev')),
    account_ids UUID[] DEFAULT '{}',
    tag_filters JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_cloud_accounts_v2_tenant_provider ON cloud_accounts_v2 (tenant_id, provider);
CREATE INDEX IF NOT EXISTS ix_cloud_accounts_v2_status ON cloud_accounts_v2 (status);
CREATE INDEX IF NOT EXISTS ix_cloud_groups_tenant_id ON cloud_groups (tenant_id);

