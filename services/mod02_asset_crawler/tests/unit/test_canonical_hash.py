"""Unit tests for Canonical State Hashing and Volatile Stripping (TC-MOD2-001)."""

import pytest
from services.mod02_asset_crawler.internal.normalizer.canonical_hasher import compute_canonical_sha256
from services.mod02_asset_crawler.internal.normalizer.volatile_stripper import strip_volatile_fields


def test_tc_mod2_001_canonical_hash_stability():
    """TC-MOD2-001: Pass two AWS S3 JSON payloads with identical settings but reversed key order
    and different ResponseMetadata.RequestId.
    
    compute_canonical_sha256() produces the exact same 64-character hex digest for both payloads.
    """
    payload_a = {
        "BucketName": "prod-customer-records",
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True,
        },
        "ServerSideEncryptionConfiguration": {
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms",
                        "KMSMasterKeyId": "arn:aws:kms:us-east-1:123456789012:key/abc-123",
                    },
                    "BucketKeyEnabled": True,
                }
            ]
        },
        "ResponseMetadata": {
            "RequestId": "AAAABBBBCCCC1111",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {"date": "Tue, 11 Nov 2026 12:00:00 GMT"},
            "RetryAttempts": 0,
        },
    }

    # Payload B has reversed key order and different RequestId / timestamps
    payload_b = {
        "ResponseMetadata": {
            "RequestId": "ZZZZYYYYXXXX9999",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {"date": "Wed, 12 Nov 2026 15:30:00 GMT"},
            "RetryAttempts": 2,
        },
        "ServerSideEncryptionConfiguration": {
            "Rules": [
                {
                    "BucketKeyEnabled": True,
                    "ApplyServerSideEncryptionByDefault": {
                        "KMSMasterKeyId": "arn:aws:kms:us-east-1:123456789012:key/abc-123",
                        "SSEAlgorithm": "aws:kms",
                    },
                }
            ]
        },
        "PublicAccessBlockConfiguration": {
            "RestrictPublicBuckets": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "BlockPublicAcls": True,
        },
        "BucketName": "prod-customer-records",
    }

    hash_a = compute_canonical_sha256(payload_a)
    hash_b = compute_canonical_sha256(payload_b)

    assert len(hash_a) == 64
    assert len(hash_b) == 64
    assert hash_a == hash_b


def test_volatile_stripping():
    sample = {
        "Name": "test-resource",
        "ETag": '"0123456789abcdef"',
        "ResponseMetadata": {"RequestId": "123"},
        "Sub": {"NextToken": "xyz", "Active": True},
    }
    cleaned = strip_volatile_fields(sample)
    assert "ETag" not in cleaned
    assert "ResponseMetadata" not in cleaned
    assert "NextToken" not in cleaned["Sub"]
    assert cleaned["Sub"]["Active"] is True
    assert cleaned["Name"] == "test-resource"

