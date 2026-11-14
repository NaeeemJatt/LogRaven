-- migrations/003_clickhouse_ocsf_activity.sql
-- ClickHouse MergeTree DDL for OCSF v1.2 Cloud Activity Storage (PRD-MOD-03)

CREATE TABLE IF NOT EXISTS ocsf_cloud_activity (
    tenant_id UUID,
    event_time DateTime64(3, 'UTC'),
    provider LowCardinality(String),
    account_id String,
    region LowCardinality(String),
    event_name LowCardinality(String),
    read_only UInt8,
    actor_user_arn String,
    actor_session_mfa UInt8,
    src_ip String,
    is_external_ip UInt8,
    geo_country FixedString(2),
    target_resource_urn String,
    status_code LowCardinality(String),
    error_code LowCardinality(String),
    raw_event_json String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_time)
ORDER BY (tenant_id, target_resource_urn, event_time, actor_user_arn);

