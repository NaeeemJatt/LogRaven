"""Unit tests for Sparse Block Reader (FR-MOD4-01)."""

import pytest

from services.mod04_disk_scanner.internal.fs_reader.sparse_reader import SparseBlockReader


@pytest.mark.asyncio
async def test_sparse_block_filtering_and_streaming():
    """Verifies sparse block reader filters out 100% zero-filled blocks and streams allocated blocks."""
    reader = SparseBlockReader(block_size=512)

    # Simulate 5 blocks: 3 unallocated (zeros), 2 allocated (actual filesystem data)
    block_0_zero = b"\x00" * 512
    block_1_data = b"EXT4_SUPERBLOCK_METADATA_HEADER" + b"\x00" * 481
    block_2_zero = b"\x00" * 512
    block_3_data = b"/var/lib/dpkg/status package manifest content" + b"\x00" * 466
    block_4_zero = b"\x00" * 512

    blocks_dict = {
        0: block_0_zero,
        1: block_1_data,
        2: block_2_zero,
        3: block_3_data,
        4: block_4_zero,
    }

    streamed_blocks = []
    async for blk in reader.stream_blocks("snap-test-001", blocks_dict):
        streamed_blocks.append(blk)

    # Exactly 2 non-zero blocks streamed (60% sparse compute/IO reduction)
    assert len(streamed_blocks) == 2
    assert streamed_blocks[0]["block_index"] == 1
    assert streamed_blocks[1]["block_index"] == 3
    assert len(streamed_blocks[0]["sha256"]) == 64
    assert streamed_blocks[0]["size"] == 512

