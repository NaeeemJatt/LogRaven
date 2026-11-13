"""Two-Stage Bulk Inventory Collector and Deep Enricher for AWS (FR-MOD2-01)."""

import asyncio
import inspect
from typing import Any, Dict, List, Optional
import boto3

from services.mod02_asset_crawler.internal.normalizer.urn_builder import build_urn
from services.mod02_asset_crawler.internal.ratelimiter.token_bucket import TokenBucketLimiter
from services.mod02_asset_crawler.internal.collectors.enrichers.s3_enricher import S3Enricher
from services.mod02_asset_crawler.internal.collectors.enrichers.ec2_enricher import EC2Enricher
from services.mod02_asset_crawler.internal.collectors.enrichers.iam_enricher import IAMEnricher


class AWSBulkCollector:
    """Discovers AWS resources in bulk and enriches configurations with bounded concurrency."""

    def __init__(
        self,
        boto_session: Optional[Any] = None,
        limiter: Optional[TokenBucketLimiter] = None,
        max_workers: int = 25,
    ):
        self.session = boto_session or boto3.Session()
        self.limiter = limiter or TokenBucketLimiter()
        self.semaphore = asyncio.Semaphore(max_workers)

    async def crawl_account(
        self,
        account_id: str,
        regions: Optional[List[str]] = None,
        s3_client: Optional[Any] = None,
        ec2_client: Optional[Any] = None,
        iam_client: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Executes Stage 1 bulk discovery followed by Stage 2 deep attribute enrichment.
        
        Returns list of standardized asset dictionaries ready for repository ingestion.
        """
        target_regions = regions or ["us-east-1"]
        s3 = s3_client or self.session.client("s3")
        iam = iam_client or self.session.client("iam")

        discovered_assets: List[Dict[str, Any]] = []

        # ── 1. S3 Buckets ──────────────────────────────────────────────
        try:
            buckets_res = await self.limiter.execute_with_backoff(
                s3.list_buckets,
                account_id=account_id,
                region="global",
                service="s3",
            )
            buckets = buckets_res.get("Buckets", [])

            async def _enrich_s3(b):
                async with self.semaphore:
                    b_name = b.get("Name")
                    config = await S3Enricher.enrich_bucket(s3, b_name)
                    urn = build_urn("aws", account_id, "global", "s3", "aws_s3_bucket", b_name)
                    return {
                        "urn": urn,
                        "provider": "aws",
                        "account_id": account_id,
                        "region": "global",
                        "service": "s3",
                        "resource_type": "aws_s3_bucket",
                        "resource_id": b_name,
                        "resource_name": b_name,
                        "config": config,
                    }

            s3_tasks = [_enrich_s3(b) for b in buckets]
            s3_results = await asyncio.gather(*s3_tasks, return_exceptions=True)
            for res in s3_results:
                if isinstance(res, dict):
                    discovered_assets.append(res)
        except Exception:
            pass

        # ── 2. EC2 Instances across regions ────────────────────────────
        for region in target_regions:
            try:
                ec2 = ec2_client or self.session.client("ec2", region_name=region)
                ec2_res = await self.limiter.execute_with_backoff(
                    ec2.describe_instances,
                    account_id=account_id,
                    region=region,
                    service="ec2",
                )
                reservations = ec2_res.get("Reservations", [])

                for r in reservations:
                    for inst in r.get("Instances", []):
                        inst_id = inst.get("InstanceId")
                        config = await EC2Enricher.enrich_instance(ec2, inst)
                        urn = build_urn("aws", account_id, region, "ec2", "aws_instance", inst_id)
                        discovered_assets.append({
                            "urn": urn,
                            "provider": "aws",
                            "account_id": account_id,
                            "region": region,
                            "service": "ec2",
                            "resource_type": "aws_instance",
                            "resource_id": inst_id,
                            "resource_name": inst_id,
                            "config": config,
                        })
            except Exception:
                pass

        # ── 3. IAM Users ───────────────────────────────────────────────
        try:
            iam_res = await self.limiter.execute_with_backoff(
                iam.list_users,
                account_id=account_id,
                region="global",
                service="iam",
            )
            users = iam_res.get("Users", [])

            for u in users:
                uname = u.get("UserName")
                config = await IAMEnricher.enrich_user(iam, u)
                urn = build_urn("aws", account_id, "global", "iam", "aws_iam_user", uname)
                discovered_assets.append({
                    "urn": urn,
                    "provider": "aws",
                    "account_id": account_id,
                    "region": "global",
                    "service": "iam",
                    "resource_type": "aws_iam_user",
                    "resource_id": uname,
                    "resource_name": uname,
                    "config": config,
                })
        except Exception:
            pass

        return discovered_assets

