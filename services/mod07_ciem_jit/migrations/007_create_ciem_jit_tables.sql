-- Migration 007: Create CIEM Entitlements and ChatOps JIT Leases Tables (PRD-MOD-07)

CREATE TABLE IF NOT EXISTS cloud_entitlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    principal_arn VARCHAR(512) NOT NULL,
    provider VARCHAR(16) NOT NULL DEFAULT 'aws', -- aws, gcp, azure
    granted_actions TEXT[] NOT NULL,
    used_actions_90d TEXT[] DEFAULT '{}',
    unused_actions_count INT DEFAULT 0,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    has_toxic_combinations BOOLEAN NOT NULL DEFAULT FALSE,
    toxic_vectors TEXT[] DEFAULT '{}',
    last_evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entitlements_principal ON cloud_entitlements(principal_arn);
CREATE INDEX IF NOT EXISTS idx_entitlements_toxic ON cloud_entitlements(has_toxic_combinations);

CREATE TABLE IF NOT EXISTS cloud_jit_leases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    requester_email VARCHAR(255) NOT NULL,
    approver_email VARCHAR(255),
    target_role_arn VARCHAR(512) NOT NULL,
    justification TEXT NOT NULL,
    duration_minutes INT NOT NULL CHECK (duration_minutes BETWEEN 15 AND 480),
    status VARCHAR(24) NOT NULL DEFAULT 'REQUESTED', -- REQUESTED | APPROVED | ACTIVE | EXPIRED | REJECTED
    session_token_id VARCHAR(128),
    activated_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jit_leases_status ON cloud_jit_leases(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_jit_leases_target_role ON cloud_jit_leases(target_role_arn);

