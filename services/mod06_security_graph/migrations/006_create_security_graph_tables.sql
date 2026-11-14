-- Migration 006: Create Security Graph, Attack Paths, and Toxic Combinations Tables (PRD-MOD-06)

CREATE TABLE IF NOT EXISTS security_graph_nodes (
    id VARCHAR(512) PRIMARY KEY,
    tenant_id UUID,
    domain VARCHAR(32) NOT NULL, -- COMPUTE, STORAGE, NETWORK, IDENTITY, VULNERABILITY, DATA
    provider VARCHAR(32) NOT NULL DEFAULT 'aws', -- aws, gcp, azure
    label VARCHAR(256) NOT NULL,
    is_internet_facing BOOLEAN NOT NULL DEFAULT FALSE,
    truerisk_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    raw_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_domain ON security_graph_nodes(domain);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_provider ON security_graph_nodes(provider);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_truerisk ON security_graph_nodes(truerisk_score DESC);

CREATE TABLE IF NOT EXISTS security_graph_edges (
    id VARCHAR(512) PRIMARY KEY,
    tenant_id UUID,
    source_id VARCHAR(512) NOT NULL REFERENCES security_graph_nodes(id) ON DELETE CASCADE,
    target_id VARCHAR(512) NOT NULL REFERENCES security_graph_nodes(id) ON DELETE CASCADE,
    relationship VARCHAR(64) NOT NULL, -- EXPOSES, ATTACHES_TO, ASSUMES_ROLE, READS_FROM, WRITES_TO, EXPLOITS
    remediation_friction DOUBLE PRECISION NOT NULL DEFAULT 1.0, -- Capacity in Min-Cut algorithm
    is_attack_path BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON security_graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON security_graph_edges(target_id);

CREATE TABLE IF NOT EXISTS security_attack_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    title VARCHAR(256) NOT NULL,
    source_node_id VARCHAR(512) NOT NULL REFERENCES security_graph_nodes(id) ON DELETE CASCADE,
    target_crown_jewel_id VARCHAR(512) NOT NULL REFERENCES security_graph_nodes(id) ON DELETE CASCADE,
    path_length INTEGER NOT NULL,
    node_path JSONB NOT NULL,
    truerisk_score DOUBLE PRECISION NOT NULL,
    chokepoint_edge_id VARCHAR(512),
    chokepoint_description TEXT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attack_paths_truerisk ON security_attack_paths(truerisk_score DESC);
CREATE INDEX IF NOT EXISTS idx_attack_paths_crown_jewel ON security_attack_paths(target_crown_jewel_id);

