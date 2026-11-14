-- migrations/005_create_runtime_reachability.sql
-- Workload Runtime Reachability and Container Drift Detection (PRD-MOD-05)

CREATE TABLE IF NOT EXISTS workload_runtime_reachability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_urn VARCHAR(512) NOT NULL REFERENCES cspm_assets(urn) ON DELETE CASCADE,
    container_id VARCHAR(128),
    package_name VARCHAR(128) NOT NULL,
    library_path VARCHAR(512) NOT NULL,
    is_loaded_in_memory BOOLEAN NOT NULL DEFAULT TRUE,
    is_container_drift BOOLEAN NOT NULL DEFAULT FALSE,
    first_executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    execution_count INT NOT NULL DEFAULT 1,
    UNIQUE (asset_urn, package_name, library_path, container_id)
);

CREATE TABLE IF NOT EXISTS container_drift_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_urn VARCHAR(512) NOT NULL REFERENCES cspm_assets(urn) ON DELETE CASCADE,
    container_id VARCHAR(128) NOT NULL,
    binary_path VARCHAR(512) NOT NULL,
    overlayfs_layer VARCHAR(64) NOT NULL DEFAULT 'upperdir',
    process_pid INT NOT NULL,
    comm VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'CRITICAL',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runtime_reach_pkg ON workload_runtime_reachability(asset_urn, package_name);
CREATE INDEX IF NOT EXISTS idx_container_drift_urn ON container_drift_alerts(asset_urn);

