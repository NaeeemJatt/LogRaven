"""Integration tests for Crawler Delta Detection, Throttling Resilience, and Tombstoning.

Covers:
- TC-MOD2-003: 500-resource crawl delta efficiency (exact mutation count)
- TC-MOD2-004: Token-bucket limiter full-jitter backoff on ThrottlingException
- TC-MOD2-005: Soft-delete tombstoning for unobserved resources
"""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest

from services.mod02_asset_crawler.internal.normalizer.urn_builder import build_urn
from services.mod02_asset_crawler.internal.publisher.kafka_publisher import AssetEventPublisher
from services.mod02_asset_crawler.internal.ratelimiter.token_bucket import TokenBucketLimiter
from services.mod02_asset_crawler.cmd.crawler.main import process_account_crawl
from services.mod02_asset_crawler.internal.repository.models import CSPMAsset


class MockDBSession:
    """Fast in-memory mock async database session simulating PostgreSQL table behavior."""

    def __init__(self):
        self.rows: dict[str, CSPMAsset] = {}

    def add(self, obj: CSPMAsset):
        self.rows[obj.urn] = obj

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def execute(self, query):
        mock_result = MagicMock()
        # Check if looking up a specific URN
        target_urn = None
        if hasattr(query, "compile"):
            compiled = query.compile()
            for v in compiled.params.values():
                if isinstance(v, str) and v.startswith("urn:lograven:"):
                    target_urn = v
                    break

        if target_urn is not None:
            if target_urn in self.rows:
                mock_result.scalar_one_or_none.return_value = self.rows[target_urn]
            else:
                mock_result.scalar_one_or_none.return_value = None
            return mock_result

        # List all active assets query
        active = [row for row in self.rows.values() if not row.is_deleted]
        mock_result.scalars.return_value.all.return_value = active
        return mock_result


@pytest.mark.asyncio
async def test_tc_mod2_003_delta_publishing_efficiency():
    """TC-MOD2-003: Crawl 500 mocked resources twice; on second crawl, mutate only 4 resources.
    
    Publisher receives exactly 4 mutation messages on second crawl (99.2% compute savings).
    """
    tenant_id = uuid.uuid4()
    account_id = "123456789012"
    session = MockDBSession()
    publisher = AssetEventPublisher()

    # Generate 500 mock resources
    resources_first_crawl = []
    for i in range(500):
        service = "s3" if i < 250 else "ec2"
        rtype = "aws_s3_bucket" if i < 250 else "aws_instance"
        rid = f"res-{i:03d}"
        urn = build_urn("aws", account_id, "us-east-1", service, rtype, rid)
        resources_first_crawl.append({
            "urn": urn,
            "region": "us-east-1",
            "service": service,
            "resource_type": rtype,
            "resource_id": rid,
            "config": {"id": rid, "status": "active", "encryption": True},
        })

    # 1. First Crawl (All 500 are new -> 500 CREATED events)
    summary_1 = await process_account_crawl(
        session=session,
        tenant_id=tenant_id,
        account_id=account_id,
        provider="aws",
        discovered_raw_assets=resources_first_crawl,
        publisher=publisher,
    )
    assert summary_1["total_discovered"] == 500
    assert summary_1["mutated_assets"] == 500
    assert len(publisher.published_events) == 500

    # Clear event log for second crawl measurement
    publisher.published_events.clear()

    # 2. Second Crawl: Mutate exactly 3 S3 buckets and 1 Security Group/EC2 instance
    resources_second_crawl = []
    mutated_indices = {10, 20, 30, 300}

    for i, res in enumerate(resources_first_crawl):
        copied = dict(res)
        copied["config"] = dict(res["config"])
        if i in mutated_indices:
            # Mutate configuration
            copied["config"]["encryption"] = False
            copied["config"]["public_access"] = True
        resources_second_crawl.append(copied)

    summary_2 = await process_account_crawl(
        session=session,
        tenant_id=tenant_id,
        account_id=account_id,
        provider="aws",
        discovered_raw_assets=resources_second_crawl,
        publisher=publisher,
    )

    assert summary_2["total_discovered"] == 500
    assert summary_2["mutated_assets"] == 4
    # Exactly 4 events emitted downstream
    assert len(publisher.published_events) == 4
    for evt in publisher.published_events:
        assert evt["change_type"] == "CONFIG_DRIFT"
        assert evt["previous_sha256"] != evt["current_sha256"]


@pytest.mark.asyncio
async def test_tc_mod2_004_rate_limiter_throttling_resilience():
    """TC-MOD2-004: Mock AWS API returning ThrottlingException on first calls; limiter backs off with full jitter."""
    limiter = TokenBucketLimiter(rate_per_second=50, burst_capacity=50)

    call_count = 0

    def mock_describe_instances():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("ThrottlingException: Rate exceeded (HTTP 429)")
        return {"Instances": [{"InstanceId": "i-ok-123"}]}

    res = await limiter.execute_with_backoff(
        mock_describe_instances,
        account_id="123456789012",
        region="us-east-1",
        service="ec2",
        max_attempts=4,
        base_backoff=0.05,
    )

    assert call_count == 3
    assert res["Instances"][0]["InstanceId"] == "i-ok-123"


@pytest.mark.asyncio
async def test_tc_mod2_005_soft_delete_tombstoning():
    """TC-MOD2-005: Remove 2 EC2 instances from provider response; rows transition to is_deleted=True and fire DELETED events."""
    tenant_id = uuid.uuid4()
    account_id = "123456789012"
    session = MockDBSession()
    publisher = AssetEventPublisher()

    # 1. First Crawl with 3 instances
    urn_1 = build_urn("aws", account_id, "us-east-1", "ec2", "aws_instance", "i-001")
    urn_2 = build_urn("aws", account_id, "us-east-1", "ec2", "aws_instance", "i-002")
    urn_3 = build_urn("aws", account_id, "us-east-1", "ec2", "aws_instance", "i-003")

    initial_assets = [
        {"urn": urn_1, "region": "us-east-1", "service": "ec2", "resource_type": "aws_instance", "resource_id": "i-001", "config": {"state": "running"}},
        {"urn": urn_2, "region": "us-east-1", "service": "ec2", "resource_type": "aws_instance", "resource_id": "i-002", "config": {"state": "running"}},
        {"urn": urn_3, "region": "us-east-1", "service": "ec2", "resource_type": "aws_instance", "resource_id": "i-003", "config": {"state": "running"}},
    ]

    await process_account_crawl(
        session=session,
        tenant_id=tenant_id,
        account_id=account_id,
        provider="aws",
        discovered_raw_assets=initial_assets,
        publisher=publisher,
    )

    publisher.published_events.clear()

    # 2. Second sweep: Instances i-002 and i-003 were terminated in AWS (only i-001 remains)
    remaining_assets = [
        {"urn": urn_1, "region": "us-east-1", "service": "ec2", "resource_type": "aws_instance", "resource_id": "i-001", "config": {"state": "running"}},
    ]

    summary = await process_account_crawl(
        session=session,
        tenant_id=tenant_id,
        account_id=account_id,
        provider="aws",
        discovered_raw_assets=remaining_assets,
        publisher=publisher,
    )

    assert summary["tombstoned_assets"] == 2
    assert summary["active_assets"] == 1

    # Check database rows
    assert session.rows[urn_1].is_deleted is False
    assert session.rows[urn_2].is_deleted is True
    assert session.rows[urn_3].is_deleted is True

    # Check published events: exactly 2 DELETED events
    assert len(publisher.published_events) == 2
    for evt in publisher.published_events:
        assert evt["change_type"] == "DELETED"
        assert evt["urn"] in (urn_2, urn_3)
