"""Integration tests for Automated 90-Day SIEM Lookback and Mutation Bridge.

Covers:
- TC-MOD3-004: Retroactive lookback finding external exploitation (1.5x multiplier)
- TC-MOD3-005: Mutating event AuthorizeSecurityGroupIngress priority re-crawl enqueue
"""

from datetime import datetime, timedelta, timezone
import pytest

from services.mod02_asset_crawler.internal.normalizer.urn_builder import build_urn
from services.mod03_ioa_siem_engine.internal.lookback.retroactive_investigator import (
    ClickHouseLookbackClient,
    RetroactiveInvestigator,
)
from services.mod03_ioa_siem_engine.internal.mutation_bridge.resource_extractor import MutationBridge


@pytest.mark.asyncio
async def test_tc_mod3_004_retroactive_siem_lookback_multiplier():
    """TC-MOD3-004: Seed ClickHouse with 90 days of S3 GetObject logs including 3 reads from external IP 185.220.101.4;
    trigger IOM-S3-PUBLIC-READ.
    
    Pass Criteria: Retroactive lookback worker attaches the 3 access records to IOM finding
    and sets siem_activity_multiplier = 1.5.
    """
    tenant_id = "tenant-lookback-001"
    account_id = "123456789012"
    target_bucket_urn = build_urn("aws", account_id, "us-east-1", "s3", "aws_s3_bucket", "confidential-data-lake")

    now = datetime.now(timezone.utc)
    ch_client = ClickHouseLookbackClient()

    # Seed 90 days of logs: mostly internal traffic, with exactly 3 external reads
    seeded_events = [
        # Internal benign read 40 days ago
        {
            "tenant_id": tenant_id,
            "target_resource_urn": target_bucket_urn,
            "event_name": "GetObject",
            "src_ip": "10.0.12.88",
            "is_external_ip": 0,
            "event_time": (now - timedelta(days=40)).isoformat(),
            "actor_user_arn": "arn:aws:iam::123456789012:role/AnalyticsWorker",
        },
        # External read 1 (30 days ago)
        {
            "tenant_id": tenant_id,
            "target_resource_urn": target_bucket_urn,
            "event_name": "GetObject",
            "src_ip": "185.220.101.4",
            "is_external_ip": 1,
            "event_time": (now - timedelta(days=30)).isoformat(),
            "actor_user_arn": "anonymous",
            "geo_country": "DE",
        },
        # External read 2 (15 days ago)
        {
            "tenant_id": tenant_id,
            "target_resource_urn": target_bucket_urn,
            "event_name": "GetObject",
            "src_ip": "185.220.101.4",
            "is_external_ip": 1,
            "event_time": (now - timedelta(days=15)).isoformat(),
            "actor_user_arn": "anonymous",
            "geo_country": "DE",
        },
        # External read 3 (2 days ago)
        {
            "tenant_id": tenant_id,
            "target_resource_urn": target_bucket_urn,
            "event_name": "GetObject",
            "src_ip": "185.220.101.4",
            "is_external_ip": 1,
            "event_time": (now - timedelta(days=2)).isoformat(),
            "actor_user_arn": "anonymous",
            "geo_country": "DE",
        },
        # Benign read on unrelated bucket
        {
            "tenant_id": tenant_id,
            "target_resource_urn": build_urn("aws", account_id, "us-east-1", "s3", "aws_s3_bucket", "public-assets"),
            "event_name": "GetObject",
            "src_ip": "185.220.101.4",
            "is_external_ip": 1,
            "event_time": (now - timedelta(days=5)).isoformat(),
        },
    ]

    ch_client.seed_events(seeded_events)
    investigator = RetroactiveInvestigator(clickhouse_client=ch_client)

    # Trigger IOM Finding
    new_finding = {
        "finding_id": "IOM-S3-PUBLIC-READ",
        "title": "S3 Bucket Permits Public Read Access",
        "target_resource_urn": target_bucket_urn,
        "base_risk_score": 7.0,
        "status": "OPEN",
    }

    result = await investigator.investigate_finding(
        finding=new_finding,
        tenant_id=tenant_id,
        lookback_days=90,
    )

    assert result["lookback_performed"] is True
    assert result["matched_external_access_count"] == 3
    assert result["siem_activity_multiplier"] == 1.5
    assert result["active_threat_detected"] is True
    # 7.0 * 1.5 = 10.5 -> capped at 10.0
    assert result["effective_risk_score"] == 10.0
    assert len(result["external_access_records"]) == 3
    for rec in result["external_access_records"]:
        assert rec["src_ip"] == "185.220.101.4"
        assert rec["target_resource_urn"] == target_bucket_urn


def test_tc_mod3_005_mutation_bridge_priority_recrawl_enqueue():
    """TC-MOD3-005: Send CloudTrail AuthorizeSecurityGroupIngress (0.0.0.0/0 on port 22) to stream worker.
    
    Pass Criteria: mutation_bridge enqueues priority job for sg-012345; target URN correctly formed.
    """
    bridge = MutationBridge()

    cloudtrail_event = {
        "eventVersion": "1.08",
        "eventTime": "2026-11-13T10:30:00Z",
        "eventName": "AuthorizeSecurityGroupIngress",
        "eventSource": "ec2.amazonaws.com",
        "awsRegion": "us-east-1",
        "recipientAccountId": "123456789012",
        "userIdentity": {
            "type": "IAMUser",
            "arn": "arn:aws:iam::123456789012:user/devops-lead",
        },
        "requestParameters": {
            "groupId": "sg-012345",
            "ipPermissions": {
                "items": [
                    {
                        "ipProtocol": "tcp",
                        "fromPort": 22,
                        "toPort": 22,
                        "ipRanges": {"items": [{"cidrIp": "0.0.0.0/0"}]},
                    }
                ]
            },
        },
    }

    job = bridge.extract_and_enqueue(cloudtrail_event)

    assert job is not None
    assert job["priority"] == "HIGH"
    assert job["resource_id"] == "sg-012345"
    assert job["account_id"] == "123456789012"
    assert job["region"] == "us-east-1"
    assert job["trigger_event"] == "AuthorizeSecurityGroupIngress"
    assert job["target_urn"] == "urn:lograven:aws:123456789012:us-east-1:ec2:aws_security_group/sg-012345"
    assert len(bridge.enqueued_jobs) == 1

