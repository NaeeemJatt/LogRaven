"""Deep configuration enricher for AWS S3 Buckets."""

import inspect
from typing import Any, Dict, Optional


class S3Enricher:
    """Enriches basic S3 bucket inventory with security posture attributes."""

    @staticmethod
    async def enrich_bucket(s3_client: Any, bucket_name: str) -> Dict[str, Any]:
        """Collects S3 PublicAccessBlock, Encryption, Policy, and Versioning."""
        enriched: Dict[str, Any] = {
            "name": bucket_name,
            "public_access_block": {},
            "encryption": {},
            "versioning": {},
        }

        # 1. Public Access Block
        try:
            res = s3_client.get_public_access_block(Bucket=bucket_name)
            if inspect.iscoroutine(res):
                res = await res
            pab = res.get("PublicAccessBlockConfiguration", {})
            enriched["public_access_block"] = {
                "block_public_acls": pab.get("BlockPublicAcls", False),
                "ignore_public_acls": pab.get("IgnorePublicAcls", False),
                "block_public_policy": pab.get("BlockPublicPolicy", False),
                "restrict_public_buckets": pab.get("RestrictPublicBuckets", False),
            }
        except Exception:
            enriched["public_access_block"] = {
                "block_public_acls": False,
                "ignore_public_acls": False,
                "block_public_policy": False,
                "restrict_public_buckets": False,
            }

        # 2. Server Side Encryption
        try:
            res = s3_client.get_bucket_encryption(Bucket=bucket_name)
            if inspect.iscoroutine(res):
                res = await res
            rules = res.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
            enriched["encryption"] = {"rules": rules, "enabled": len(rules) > 0}
        except Exception:
            enriched["encryption"] = {"enabled": False, "rules": []}

        # 3. Versioning
        try:
            res = s3_client.get_bucket_versioning(Bucket=bucket_name)
            if inspect.iscoroutine(res):
                res = await res
            enriched["versioning"] = {"status": res.get("Status", "Disabled")}
        except Exception:
            enriched["versioning"] = {"status": "Disabled"}

        return enriched

