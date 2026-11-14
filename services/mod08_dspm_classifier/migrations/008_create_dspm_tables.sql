-- Migration 008: Create DSPM Data Assets and Classifications Tables (PRD-MOD-08)

CREATE TABLE IF NOT EXISTS dspm_data_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_urn VARCHAR(512) NOT NULL,
    tenant_id UUID,
    storage_type VARCHAR(32) NOT NULL,          -- s3, blob, gcs, rds_postgres, bigquery
    total_objects_count BIGINT NOT NULL DEFAULT 0,
    sampled_objects_count INT NOT NULL DEFAULT 0,
    contains_pii BOOLEAN NOT NULL DEFAULT FALSE,
    contains_pci BOOLEAN NOT NULL DEFAULT FALSE,
    contains_phi BOOLEAN NOT NULL DEFAULT FALSE,
    contains_secrets BOOLEAN NOT NULL DEFAULT FALSE,
    encryption_type VARCHAR(32) NOT NULL DEFAULT 'SSE_DEFAULT', -- NONE | SSE_DEFAULT | CMK_KMS
    is_ransomware_vulnerable BOOLEAN NOT NULL DEFAULT FALSE, -- Missing versioning / immutable lock
    scanned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dspm_assets_urn ON dspm_data_assets(asset_urn);
CREATE INDEX IF NOT EXISTS idx_dspm_assets_risk ON dspm_data_assets(contains_pci, contains_pii, contains_secrets);

CREATE TABLE IF NOT EXISTS dspm_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_asset_id UUID NOT NULL REFERENCES dspm_data_assets(id) ON DELETE CASCADE,
    tenant_id UUID,
    category VARCHAR(32) NOT NULL,              -- PII | PCI | PHI | SECRET
    detector_name VARCHAR(64) NOT NULL,         -- CREDIT_CARD_VISA, US_SSN, AWS_SECRET_KEY
    confidence VARCHAR(16) NOT NULL,            -- HIGH | MEDIUM
    match_count INT NOT NULL DEFAULT 1,
    file_extension VARCHAR(16) NOT NULL DEFAULT '',
    byte_offset INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dspm_classifications_asset ON dspm_classifications(data_asset_id);
CREATE INDEX IF NOT EXISTS idx_dspm_classifications_cat ON dspm_classifications(category);
