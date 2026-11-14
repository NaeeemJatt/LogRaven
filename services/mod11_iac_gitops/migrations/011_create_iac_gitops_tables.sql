-- migrations/011_create_iac_gitops_tables.sql
-- Module 11: ASPM, IaC AST Scanner, & Code-to-Cloud GitOps Auto-PR (PRD-MOD-11)

CREATE TABLE IF NOT EXISTS git_repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    provider VARCHAR(16) NOT NULL CHECK (provider IN ('github', 'gitlab', 'bitbucket')),
    repo_full_name VARCHAR(256) NOT NULL,       -- owner/repo
    default_branch VARCHAR(64) NOT NULL DEFAULT 'main',
    installation_id VARCHAR(128) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, provider, repo_full_name)
);

CREATE INDEX IF NOT EXISTS idx_git_repos_tenant ON git_repositories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_git_repos_name ON git_repositories(repo_full_name);

CREATE TABLE IF NOT EXISTS iac_lineage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_urn VARCHAR(512) NOT NULL,
    repo_id UUID NOT NULL REFERENCES git_repositories(id) ON DELETE CASCADE,
    file_path VARCHAR(512) NOT NULL,            -- terraform/s3.tf
    start_line INT NOT NULL,
    end_line INT NOT NULL,
    resource_block_name VARCHAR(128) NOT NULL,  -- aws_s3_bucket.customer_data
    commit_sha CHAR(40) NOT NULL,
    last_verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_iac_lineage_asset ON iac_lineage_records(asset_urn);
CREATE INDEX IF NOT EXISTS idx_iac_lineage_repo ON iac_lineage_records(repo_id);

CREATE TABLE IF NOT EXISTS gitops_remediation_prs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    finding_id UUID,
    repo_id UUID NOT NULL REFERENCES git_repositories(id),
    pr_number INT NOT NULL,
    pr_url TEXT NOT NULL,
    branch_name VARCHAR(128) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'OPEN', -- OPEN | MERGED | CLOSED
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gitops_prs_repo ON gitops_remediation_prs(repo_id);
CREATE INDEX IF NOT EXISTS idx_gitops_prs_finding ON gitops_remediation_prs(finding_id);
