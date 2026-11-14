-- migrations/012_create_policy_vault_tables.sql
-- Module 12: Visual-to-Rego Studio, Dual-Engine Suppressions, & Cryptographic Audit Vault (PRD-MOD-12)

CREATE TABLE IF NOT EXISTS custom_rego_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    rule_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    severity VARCHAR(16) NOT NULL DEFAULT 'HIGH',
    resource_type VARCHAR(64) NOT NULL,
    visual_ast JSONB NOT NULL DEFAULT '{}',
    rego_code TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_custom_rules_tenant ON custom_rego_rules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_custom_rules_resource ON custom_rego_rules(resource_type);

CREATE TABLE IF NOT EXISTS crowdstrike_suppression_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    name VARCHAR(128) NOT NULL,
    finding_type VARCHAR(64),                    -- e.g. IOM-S3-PUBLIC-ACL
    account_ids TEXT[] NOT NULL DEFAULT '{}',
    regions TEXT[] NOT NULL DEFAULT '{}',
    tag_filters JSONB NOT NULL DEFAULT '{}',
    justification TEXT NOT NULL,
    approver VARCHAR(128) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE | EXPIRED | REVOKED
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_suppressions_tenant ON crowdstrike_suppression_rules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_suppressions_status ON crowdstrike_suppression_rules(status);
CREATE INDEX IF NOT EXISTS idx_suppressions_expires ON crowdstrike_suppression_rules(expires_at);

CREATE TABLE IF NOT EXISTS vault_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    package_name VARCHAR(128) NOT NULL,
    merkle_root_hash CHAR(64) NOT NULL,
    file_hashes JSONB NOT NULL DEFAULT '{}',
    package_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vault_packages_tenant ON vault_packages(tenant_id);
