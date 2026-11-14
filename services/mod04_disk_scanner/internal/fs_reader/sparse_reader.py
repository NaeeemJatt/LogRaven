"""Sparse Block Reader: Reads only non-zero allocated blocks via EBS Direct APIs (FR-MOD4-01)."""

import hashlib
from typing import Any, AsyncGenerator, Dict, List, Optional


class SparseBlockReader:
    """Streams allocated, non-zero blocks from a cloud disk snapshot.
    
    Eliminates the need to mount or download the full volume image.
    """

    def __init__(self, block_size: int = 524288):
        self.block_size = block_size  # 512 KiB

    @staticmethod
    def is_zero_block(data: bytes) -> bool:
        """Determines if a block is entirely zero-filled (unallocated)."""
        if not data:
            return True
        return data == b"\x00" * len(data)

    async def list_allocated_blocks(
        self,
        snapshot_id: str,
        total_blocks: int = 100,
        allocated_indices: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """Simulates/calls ebs:ListSnapshotBlocks returning indices of non-empty data blocks."""
        indices = allocated_indices if allocated_indices is not None else list(range(0, total_blocks, 4))
        blocks = []
        for idx in indices:
            blocks.append({
                "block_index": idx,
                "block_token": f"token-{snapshot_id}-{idx}",
                "block_size": self.block_size,
            })
        return blocks

    async def stream_blocks(
        self,
        snapshot_id: str,
        blocks_data: Dict[int, bytes],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streams only non-zero allocated blocks."""
        for idx, raw_bytes in blocks_data.items():
            if self.is_zero_block(raw_bytes):
                continue

            block_hash = hashlib.sha256(raw_bytes).hexdigest()
            yield {
                "block_index": idx,
                "data": raw_bytes,
                "sha256": block_hash,
                "size": len(raw_bytes),
            }

