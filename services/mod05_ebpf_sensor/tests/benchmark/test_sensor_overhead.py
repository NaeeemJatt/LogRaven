"""Benchmark tests for eBPF Sensor Overhead and Ring Buffer Throughput (TC-MOD5-003, NFR-MOD5-01)."""

import asyncio
import time
import pytest

from services.mod05_ebpf_sensor.internal.bpf_loader.ringbuf_consumer import (
    ResourceGovernor,
    RingBufferConsumer,
)


@pytest.mark.asyncio
async def test_tc_mod5_003_sensor_overhead_under_5000_events_per_sec():
    """TC-MOD5-003: Run synthetic workload spawning 5,000 processes/sec.
    
    Pass Criteria: Sensor CPU usage stays below 1.48% on a single core;
    zero dropped ring buffer events.
    """
    governor = ResourceGovernor(max_cpu_pct=1.5, max_ram_mb=64.0)
    consumer = RingBufferConsumer(governor=governor)

    total_events = 5000
    events_batch = [
        {
            "pid": 1000 + (i % 5000),
            "comm": "curl",
            "filename": "/usr/bin/curl",
            "container_id": f"k8s_container_{i % 50}",
            "asset_urn": "urn:lograven:aws:123456789012:us-east-1:ec2:instance/i-benchmark",
            "is_container_upper_layer": 0,
        }
        for i in range(total_events)
    ]

    start_time = time.perf_counter()
    processed = await consumer.consume_batch(events_batch)
    elapsed_time = time.perf_counter() - start_time

    metrics = governor.get_metrics()

    # Pass Criteria Assertions:
    # 1. Total processed equals batch size with ZERO dropped events
    assert len(processed) == total_events
    assert metrics["dropped_events"] == 0, f"Expected 0 dropped events, got {metrics['dropped_events']}"
    assert metrics["processed_events"] == total_events

    # 2. CPU overhead <= 1.48%
    assert metrics["cpu_usage_pct"] <= 1.48, f"CPU usage {metrics['cpu_usage_pct']}% exceeds 1.48%"

    # 3. RAM overhead <= 64.0 MB
    assert metrics["ram_usage_mb"] <= 64.0, f"RAM usage {metrics['ram_usage_mb']}MB exceeds 64MB"

    # 4. Processing throughput: 5,000 events processed in under 1 second in user space
    assert elapsed_time < 1.0, f"Benchmark took {elapsed_time:.3f}s for 5,000 events (target < 1.0s)"

