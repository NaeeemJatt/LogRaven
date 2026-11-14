"""S3 Range-Request Partial Byte Streamer (FR-MOD8-01, TC-MOD8-002).

Fetches at most 64 KB (65,536 bytes) per sampled S3 key using HTTP Range headers,
avoiding expensive full-object downloads and preventing raw data exfiltration.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional
from services.mod08_dspm_classifier.internal.sampler.reservoir import ReservoirSampler

MAX_SAMPLE_BYTES = 65536  # 64 KB


class S3RangeSampler:
    """Streams partial byte ranges from sampled S3 objects."""

    def __init__(self, k_sample_size: int = 200, max_bytes: int = MAX_SAMPLE_BYTES):
        self.k_sample_size = k_sample_size
        self.max_bytes = max_bytes
        self.reservoir = ReservoirSampler(k=k_sample_size)

    def select_sample_keys(self, all_keys: List[str]) -> List[str]:
        """Applies Algorithm R to select at most k = 200 keys uniformly."""
        return self.reservoir.sample(all_keys)

    async def fetch_byte_range(
        self,
        s3_client,
        bucket_name: str,
        key: str,
    ) -> bytes:
        """Fetches at most 64 KB using HTTP Range: bytes=0-65535."""
        if not s3_client:
            return b""

        try:
            resp = await s3_client.get_object(
                Bucket=bucket_name,
                Key=key,
                Range=f"bytes=0-{self.max_bytes - 1}",
            )
            data = await resp["Body"].read()
            return data[:self.max_bytes]
        except Exception:
            return b""
