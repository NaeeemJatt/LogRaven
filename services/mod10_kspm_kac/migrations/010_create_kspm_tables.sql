-- migrations/010_create_kspm_tables.sql
-- Module 10: KSPM & Kubernetes Admission Controller (KAC) Webhook (PRD-MOD-10)

CREATE TABLE IF NOT EXISTS k8s_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_urn VARCHAR(512) NOT NULL,
    tenant_id UUID,
    cluster_name VARCHAR(128) NOT NULL,
    distribution VARCHAR(32) NOT NULL DEFAULT 'EKS',          -- EKS | AKS | GKE | ON_PREM
    k8s_version VARCHAR(32) NOT NULL DEFAULT 'v1.30.0',
    kac_webhook_installed BOOLEAN NOT NULL DEFAULT FALSE,
    kac_enforcement_mode VARCHAR(16) NOT NULL DEFAULT 'AUDIT', -- AUDIT | ENFORCE
    namespaces_count INT NOT NULL DEFAULT 0,
    pods_count INT NOT NULL DEFAULT 0,
    last_crawled_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_k8s_clusters_urn ON k8s_clusters(asset_urn);
CREATE INDEX IF NOT EXISTS idx_k8s_clusters_tenant ON k8s_clusters(tenant_id);

CREATE TABLE IF NOT EXISTS k8s_admission_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID NOT NULL REFERENCES k8s_clusters(id) ON DELETE CASCADE,
    tenant_id UUID,
    resource_kind VARCHAR(64) NOT NULL,         -- Pod, Deployment, DaemonSet, StatefulSet
    resource_name VARCHAR(128) NOT NULL,
    namespace VARCHAR(128) NOT NULL,
    operation VARCHAR(16) NOT NULL,             -- CREATE | UPDATE | DELETE
    allowed BOOLEAN NOT NULL,
    violated_policies JSONB NOT NULL DEFAULT '[]',
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_k8s_admission_cluster ON k8s_admission_events(cluster_id);
CREATE INDEX IF NOT EXISTS idx_k8s_admission_evaluated ON k8s_admission_events(evaluated_at);
