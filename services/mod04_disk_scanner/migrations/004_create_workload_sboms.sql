-- migrations/004_create_workload_sboms.sql
-- Workload SBOMs and CVE Vulnerabilities (PRD-MOD-04)

CREATE TABLE IF NOT EXISTS workload_sboms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_urn VARCHAR(512) NOT NULL REFERENCES cspm_assets(urn) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    os_family VARCHAR(64) NOT NULL,            -- ubuntu, debian, rhel, alpine, amzn
    os_version VARCHAR(64) NOT NULL,
    kernel_version VARCHAR(128),
    cyclonedx_sbom JSONB NOT NULL,              -- Full CycloneDX v1.5 JSON representation
    packages_count INT NOT NULL DEFAULT 0,
    scan_duration_sec INT NOT NULL DEFAULT 0,
    scanned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workload_vulnerabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_urn VARCHAR(512) NOT NULL REFERENCES cspm_assets(urn) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    cve_id VARCHAR(32) NOT NULL,                -- CVE-2026-XXXX
    package_name VARCHAR(128) NOT NULL,
    installed_version VARCHAR(64) NOT NULL,
    fixed_version VARCHAR(64),
    cvss_v3_score NUMERIC(3, 1) NOT NULL,
    is_cisa_kev BOOLEAN NOT NULL DEFAULT FALSE,
    epss_score NUMERIC(5, 4) NOT NULL DEFAULT 0.0,
    first_detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remediated_at TIMESTAMPTZ,
    UNIQUE (asset_urn, cve_id, package_name)
);

CREATE INDEX IF NOT EXISTS idx_workload_sboms_urn ON workload_sboms(asset_urn);
CREATE INDEX IF NOT EXISTS idx_workload_vulns_urn ON workload_vulnerabilities(asset_urn);
CREATE INDEX IF NOT EXISTS idx_workload_vulns_cve ON workload_vulnerabilities(cve_id);
CREATE INDEX IF NOT EXISTS idx_workload_vulns_kev ON workload_vulnerabilities(is_cisa_kev) WHERE is_cisa_kev = TRUE;

