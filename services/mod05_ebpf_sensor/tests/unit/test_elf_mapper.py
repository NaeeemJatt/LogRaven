"""Unit tests for Process and ELF Package Resolver (TC-MOD5-001)."""

import time
import pytest

from services.mod05_ebpf_sensor.internal.mapper.elf_reader import ELFReader
from services.mod05_ebpf_sensor.internal.mapper.proc_resolver import ProcessResolver


def test_tc_mod5_001_curl_binary_package_resolution():
    """TC-MOD5-001: Execute /usr/bin/curl on host; ring buffer receives exec event.
    
    Pass Criteria: proc_resolver correlates /usr/bin/curl to package curl (v7.88.1) in < 2ms.
    """
    resolver = ProcessResolver()

    start_perf = time.perf_counter()
    result = resolver.resolve("/usr/bin/curl")
    elapsed_ms = (time.perf_counter() - start_perf) * 1000.0

    assert result is not None, "Failed to resolve /usr/bin/curl"
    assert result["package_name"] == "curl"
    assert "7.88.1" in result["package_version"]
    assert elapsed_ms < 2.0, f"Resolution took {elapsed_ms:.3f}ms, expected < 2ms"


def test_shared_library_openssl_resolution():
    """Verifies shared objects (libssl.so.3) map directly to parent package (openssl)."""
    resolver = ProcessResolver()

    result = resolver.resolve("/usr/lib/x86_64-linux-gnu/libssl.so.3")
    assert result is not None
    assert result["package_name"] == "openssl"
    assert "3.0.11" in result["package_version"]


def test_elf_header_validation():
    """Verifies ELF header detection."""
    valid_elf = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8
    non_elf = b"#!/bin/bash\necho hello"

    assert ELFReader.is_elf_binary(valid_elf) is True
    assert ELFReader.is_elf_binary(non_elf) is False

