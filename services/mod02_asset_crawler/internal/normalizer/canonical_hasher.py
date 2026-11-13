"""Canonical JSON State Hasher for CSPM Configuration Drift Tracking (FR-MOD2-03, TC-MOD2-001)."""

import hashlib
import json
from typing import Any, Dict, Tuple
from services.mod02_asset_crawler.internal.normalizer.volatile_stripper import strip_volatile_fields


def compute_canonical_sha256(data: Dict[str, Any]) -> str:
    """Computes a deterministic 64-character SHA-256 hex digest for arbitrary cloud configurations.
    
    1. Recursively strips volatile API metadata (ResponseMetadata, RequestId, etag).
    2. Serializes with sorted keys and compact separators.
    3. Computes SHA-256 digest over normalized UTF-8 bytes.
    """
    cleaned = strip_volatile_fields(data)
    canonical_json = json.dumps(
        cleaned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def canonicalize_config(data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Returns tuple of (cleaned_dict, sha256_hash)."""
    cleaned = strip_volatile_fields(data)
    canonical_json = json.dumps(
        cleaned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return cleaned, digest

