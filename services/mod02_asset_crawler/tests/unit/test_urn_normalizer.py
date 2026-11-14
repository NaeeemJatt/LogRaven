"""Unit tests for Canonical URN Builder & Parser (TC-MOD2-002)."""

import pytest
from services.mod02_asset_crawler.internal.normalizer.urn_builder import (
    build_urn,
    parse_urn,
    URN_REGEX,
)


def test_tc_mod2_002_urn_builder_cross_cloud():
    """TC-MOD2-002: Test build_urn() across AWS EC2, Azure KeyVault, GCP BigQuery, OCI Bucket, and K8s Deployment.
    
    All 5 URNs match regex ^urn:lograven:(aws|azure|gcp|oci|alibaba|k8s|saas):[^:]+:[^:]+:[^:]+:[^/]+/.+$.
    """
    urn_aws = build_urn("aws", "123456789012", "us-east-1", "ec2", "aws_instance", "i-0abcdef1234567890")
    urn_azure = build_urn("azure", "sub-uuid-1111", "eastus", "keyvault", "vault", "kv-prod-sec")
    urn_gcp = build_urn("gcp", "my-gcp-project", "us-central1", "bigquery", "dataset", "analytics_ds")
    urn_oci = build_urn("oci", "ocid1.tenancy.oc1..aaaa", "us-ashburn-1", "objectstorage", "bucket", "secure-logs")
    urn_k8s = build_urn("k8s", "prod-cluster-us", "default", "apps", "deployment", "auth-api")

    test_urns = [urn_aws, urn_azure, urn_gcp, urn_oci, urn_k8s]

    for urn in test_urns:
        assert URN_REGEX.match(urn), f"URN '{urn}' failed regex match"

    assert urn_aws == "urn:lograven:aws:123456789012:us-east-1:ec2:aws_instance/i-0abcdef1234567890"
    assert urn_azure == "urn:lograven:azure:sub-uuid-1111:eastus:keyvault:vault/kv-prod-sec"
    assert urn_gcp == "urn:lograven:gcp:my-gcp-project:us-central1:bigquery:dataset/analytics_ds"
    assert urn_k8s == "urn:lograven:k8s:prod-cluster-us:default:apps:deployment/auth-api"


def test_urn_parser_round_trip():
    urn = "urn:lograven:aws:999888777666:global:s3:aws_s3_bucket/my-raw-data"
    parsed = parse_urn(urn)

    assert parsed["provider"] == "aws"
    assert parsed["account_id"] == "999888777666"
    assert parsed["region"] == "global"
    assert parsed["service"] == "s3"
    assert parsed["resource_type"] == "aws_s3_bucket"
    assert parsed["resource_id"] == "my-raw-data"


def test_urn_builder_validations():
    with pytest.raises(ValueError, match="Invalid cloud provider"):
        build_urn("unsupported_cloud", "123", "us-east-1", "s3", "bucket", "name")

    with pytest.raises(ValueError, match="resource_id cannot be empty"):
        build_urn("aws", "123", "us-east-1", "s3", "bucket", "")

