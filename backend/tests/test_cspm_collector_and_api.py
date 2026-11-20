# LogRaven — Module 08 Test Suite: AWS Collector & FastAPI CSPM Router
# Tests AWSStateAndLogCollector (with mock boto3 clients) and FastAPI endpoints:
# /api/v1/cspm/catalogs/summary, /api/v1/cspm/evaluate/non-ai, /api/v1/cspm/ingest-logs.

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.collectors.aws_collector import AWSStateAndLogCollector, _calc_age_days
from app.main import app


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# ── Collector Tests ──────────────────────────────────────────────────────────


def test_calc_age_days():
    # Null or empty returns 9999
    assert _calc_age_days(None) == 9999
    assert _calc_age_days("") == 9999
    # Current date should be ~0 days
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    assert _calc_age_days(now_iso) == 0


def test_collector_iam_credential_report_and_roles():
    mock_iam = MagicMock()

    # CSV credential report with Alice (mfa false) and Bob (mfa true)
    csv_report = (
        "user,arn,user_creation_time,password_enabled,password_last_used,password_last_changed,password_next_rotation,mfa_active,access_key_1_active,access_key_1_last_rotated,access_key_2_active,access_key_2_last_rotated\n"
        "alice,arn:aws:iam::123456789012:user/alice,2026-01-01T00:00:00+00:00,true,2026-10-01T00:00:00+00:00,2026-01-01T00:00:00+00:00,N/A,false,true,2026-01-01T00:00:00+00:00,false,N/A\n"
        "bob,arn:aws:iam::123456789012:user/bob,2026-01-01T00:00:00+00:00,true,2026-11-01T00:00:00+00:00,2026-11-01T00:00:00+00:00,N/A,true,false,N/A,false,N/A\n"
    )
    mock_iam.get_credential_report.return_value = {"Content": csv_report.encode("utf-8")}
    mock_iam.list_users.return_value = {
        "Users": [
            {"UserName": "alice", "Arn": "arn:aws:iam::123456789012:user/alice"},
            {"UserName": "bob", "Arn": "arn:aws:iam::123456789012:user/bob"},
        ]
    }
    mock_iam.list_user_policies.return_value = {"PolicyNames": []}

    # Role with wildcard policy
    wildcard_policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
    }
    mock_iam.list_roles.return_value = {
        "Roles": [
            {"RoleName": "AdminRole", "RoleId": "AROA123", "Arn": "arn:aws:iam::123456789012:role/AdminRole"}
        ]
    }
    mock_iam.list_role_policies.return_value = {"PolicyNames": ["AdminInline"]}
    mock_iam.get_role_policy.return_value = {"PolicyDocument": wildcard_policy}

    collector = AWSStateAndLogCollector(iam_client=mock_iam)
    iam_state = collector.collect_iam_state()

    assert len(iam_state) >= 3  # alice, bob, AdminRole

    # Check Alice
    alice_item = next(r for r in iam_state if r.get("user") == "alice")
    assert alice_item["mfa_active"] is False
    assert alice_item["credential_age_days"] > 0

    # Check Bob
    bob_item = next(r for r in iam_state if r.get("user") == "bob")
    assert bob_item["mfa_active"] is True

    # Check AdminRole
    role_item = next(r for r in iam_state if r.get("RoleName") == "AdminRole")
    assert role_item["PolicyDocument"]["Statement"][0]["Action"] == "*"


def test_collector_security_groups():
    mock_ec2 = MagicMock()
    mock_ec2.describe_security_groups.return_value = {
        "SecurityGroups": [
            {
                "GroupId": "sg-0123456789abcdef0",
                "GroupName": "open-ssh-sg",
                "Description": "Insecure SG",
                "VpcId": "vpc-001",
                "IpPermissions": [
                    {
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpProtocol": "tcp",
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    }
                ],
            }
        ]
    }

    collector = AWSStateAndLogCollector(ec2_client=mock_ec2)
    sgs = collector.collect_security_groups()

    assert len(sgs) == 1
    assert sgs[0]["GroupId"] == "sg-0123456789abcdef0"
    assert sgs[0]["service"] == "SECURITY_GROUP"
    assert sgs[0]["IpPermissions"][0]["FromPort"] == 22
    assert sgs[0]["IpPermissions"][0]["IpRanges"][0]["CidrIp"] == "0.0.0.0/0"


def test_collector_ec2_instances():
    mock_ec2 = MagicMock()
    mock_ec2.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}
    mock_ec2.describe_instances.return_value = {
        "Reservations": [
            {
                "OwnerId": "123456789012",
                "Instances": [
                    {
                        "InstanceId": "i-0abcdef1234567890",
                        "InstanceType": "t3.medium",
                        "State": {"Name": "running"},
                        "PublicIpAddress": "54.210.10.20",
                        "PrivateIpAddress": "10.0.1.5",
                        "VpcId": "vpc-001",
                        "SubnetId": "subnet-001",
                        "Tags": [{"Key": "Name", "Value": "prod-web-server"}],
                    }
                ],
            }
        ]
    }
    mock_ec2.get_paginator.return_value.paginate.return_value = [mock_ec2.describe_instances.return_value]

    collector = AWSStateAndLogCollector(ec2_client=mock_ec2)
    instances = collector.collect_ec2_instances()

    assert len(instances) == 1
    assert instances[0]["InstanceId"] == "i-0abcdef1234567890"
    assert instances[0]["name"] == "prod-web-server"
    assert instances[0]["resource_type"] == "instance"
    assert instances[0]["service"] == "EC2"
    assert instances[0]["State"] == "running"
    assert instances[0]["PublicIpAddress"] == "54.210.10.20"


def test_collector_load_balancers():
    mock_elbv2 = MagicMock()
    mock_elbv2.describe_load_balancers.return_value = {
        "LoadBalancers": [
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/prod-alb/123",
                "LoadBalancerName": "prod-alb",
                "DNSName": "prod-alb-123.us-east-1.elb.amazonaws.com",
                "Scheme": "internet-facing",
                "Type": "application",
                "State": {"Code": "active"},
                "SecurityGroups": ["sg-0123"],
            }
        ]
    }
    mock_elbv2.get_paginator.return_value.paginate.return_value = [mock_elbv2.describe_load_balancers.return_value]
    mock_elb = MagicMock()
    mock_elb.describe_load_balancers.return_value = {"LoadBalancerDescriptions": []}
    mock_elb.get_paginator.return_value.paginate.return_value = [{"LoadBalancerDescriptions": []}]

    mock_ec2 = MagicMock()
    mock_ec2.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}

    collector = AWSStateAndLogCollector(ec2_client=mock_ec2, elbv2_client=mock_elbv2, elb_client=mock_elb)
    lbs = collector.collect_load_balancers()

    assert len(lbs) == 1
    assert lbs[0]["service"] == "LOAD_BALANCER"
    assert lbs[0]["name"] == "prod-alb"
    assert lbs[0]["Scheme"] == "internet-facing"
    assert lbs[0]["open_to_world"] is True


def test_collector_log_groups():
    mock_logs = MagicMock()
    mock_logs.describe_log_groups.return_value = {
        "logGroups": [
            {
                "logGroupName": "/aws/vpc/flowlogs/prod",
                "arn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/vpc/flowlogs/prod:*",
                "retentionInDays": 365,
                "kmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/custom-key-1",
            }
        ]
    }
    mock_logs.get_paginator.return_value.paginate.return_value = [mock_logs.describe_log_groups.return_value]
    mock_ec2 = MagicMock()
    mock_ec2.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}

    collector = AWSStateAndLogCollector(ec2_client=mock_ec2, logs_client=mock_logs)
    lgs = collector.collect_log_groups()

    assert len(lgs) == 1
    assert lgs[0]["service"] == "LOG_GROUP"
    assert lgs[0]["name"] == "/aws/vpc/flowlogs/prod"
    assert lgs[0]["retentionInDays"] == 365
    assert lgs[0]["encryption_enabled"] is True


def test_collector_api_gateways():
    mock_ag1 = MagicMock()
    mock_ag1.get_rest_apis.return_value = {
        "items": [{"id": "rest-123", "name": "core-rest-api", "endpointConfiguration": {"types": ["REGIONAL"]}}]
    }
    mock_ag2 = MagicMock()
    mock_ag2.get_apis.return_value = {
        "Items": [{"ApiId": "http-456", "Name": "telemetry-http", "ProtocolType": "HTTP", "ApiEndpoint": "https://api.test.com"}]
    }
    mock_ec2 = MagicMock()
    mock_ec2.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}

    collector = AWSStateAndLogCollector(ec2_client=mock_ec2, apigateway_client=mock_ag1, apigatewayv2_client=mock_ag2)
    apis = collector.collect_api_gateways()

    assert len(apis) == 2
    assert apis[0]["service"] == "API_GATEWAY"
    assert apis[0]["protocol"] == "REST"
    assert apis[1]["service"] == "API_GATEWAY"
    assert apis[1]["protocol"] == "HTTP"


def test_collector_lambda_functions():
    mock_lambda = MagicMock()
    mock_lambda.list_functions.return_value = {
        "Functions": [
            {
                "FunctionName": "auth-authorizer",
                "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:auth-authorizer",
                "Runtime": "python3.11",
                "Timeout": 15,
            }
        ]
    }
    mock_lambda.get_paginator.return_value.paginate.return_value = [mock_lambda.list_functions.return_value]
    mock_ec2 = MagicMock()
    mock_ec2.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}

    collector = AWSStateAndLogCollector(ec2_client=mock_ec2, lambda_client=mock_lambda)
    fns = collector.collect_lambda_functions()

    assert len(fns) == 1
    assert fns[0]["service"] == "LAMBDA"
    assert fns[0]["name"] == "auth-authorizer"
    assert fns[0]["Runtime"] == "python3.11"


def test_collector_s3_and_kms():
    mock_s3 = MagicMock()
    mock_s3.list_buckets.return_value = {
        "Buckets": [{"Name": "prod-financial-vault"}]
    }
    mock_s3.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms",
                        "KMSMasterKeyId": "arn:aws:kms:us-east-1:123456789012:key/custom-key-1",
                    }
                }
            ]
        }
    }
    mock_s3.get_public_access_block.return_value = {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }
    }
    mock_s3.get_bucket_policy.return_value = {"Policy": '{"Version":"2012-10-17","Statement":[]}'}

    mock_kms = MagicMock()
    mock_kms.list_keys.return_value = {"Keys": [{"KeyId": "custom-key-1"}]}
    mock_kms.describe_key.return_value = {
        "KeyMetadata": {
            "KeyId": "custom-key-1",
            "Arn": "arn:aws:kms:us-east-1:123456789012:key/custom-key-1",
            "KeyManager": "CUSTOMER",
            "Enabled": True,
        }
    }
    mock_kms.get_key_rotation_status.return_value = {"KeyRotationEnabled": True}

    collector = AWSStateAndLogCollector(s3_client=mock_s3, kms_client=mock_kms)
    s3_res = collector.collect_s3_buckets()
    kms_res = collector.collect_kms_keys()

    assert len(s3_res) == 1
    assert s3_res[0]["Name"] == "prod-financial-vault"
    assert s3_res[0]["encryption_enabled"] is True
    assert s3_res[0]["PublicAccessBlockConfiguration"]["BlockPublicAcls"] is True

    assert len(kms_res) == 1
    assert kms_res[0]["KeyRotationEnabled"] is True
    assert kms_res[0]["KeyManager"] == "CUSTOMER"


def test_collector_unified_collect_all():
    mock_ec2 = MagicMock()
    mock_ec2.describe_security_groups.return_value = {"SecurityGroups": []}
    mock_ec2.describe_regions.return_value = {"Regions": [{"RegionName": "us-east-1"}]}
    mock_ec2.describe_instances.return_value = {"Reservations": []}
    mock_s3 = MagicMock()
    mock_s3.list_buckets.return_value = {"Buckets": []}

    collector = AWSStateAndLogCollector(ec2_client=mock_ec2, s3_client=mock_s3)
    resources = collector.collect_all_resources(services=["EC2", "SECURITY_GROUP", "LOAD_BALANCER", "S3"])

    assert "EC2" in resources
    assert "SECURITY_GROUP" in resources
    assert "LOAD_BALANCER" in resources
    assert "S3" in resources
    assert isinstance(resources["EC2"], list)
    assert isinstance(resources["SECURITY_GROUP"], list)
    assert isinstance(resources["LOAD_BALANCER"], list)
    assert isinstance(resources["S3"], list)


# ── FastAPI Router Endpoints Tests ───────────────────────────────────────────


def test_api_catalogs_summary(client: TestClient):
    response = client.get("/api/v1/cspm/catalogs/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["non_ai_guarantee"] is True
    assert data["total_rules"] == 1565
    assert data["total_cids"] == 1565
    assert data["policies_count"] == 29
    assert data["mandates_count"] == 38
    assert "AWS" in data["providers"]
    assert data["rules_by_provider"]["AWS"] == 700
    assert "CIDR_OPEN_WORLD" in data["supported_operators"]


def test_api_evaluate_non_ai(client: TestClient):
    payload = {
        "provider": "AWS",
        "account_id": "112233445566",
        "resources_by_service": {
            "VPC": [
                {
                    "urn": "arn:aws:ec2:us-east-1:112233445566:security-group/sg-insecure",
                    "id": "sg-insecure",
                    "IpPermissions": [
                        {
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpProtocol": "tcp",
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                }
            ],
            "IAM": [
                {
                    "urn": "arn:aws:iam::112233445566:role/DangerousRole",
                    "id": "DangerousRole",
                    "Statement": [
                        {"Effect": "Allow", "Action": "*", "Resource": "*"}
                    ],
                    "PolicyDocument": {
                        "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]
                    },
                    "PolicyDocuments": [
                        {"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}
                    ],
                }
            ],
        },
        "cloudtrail_events": [],
    }

    response = client.post("/api/v1/cspm/evaluate/non-ai", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["non_ai_guarantee"] is True
    assert data["provider"] == "AWS"
    summary = data["execution_summary"]
    assert summary["total_controls_evaluated"] == 700
    assert summary["controls_failed"] >= 2  # CID 41 and CID 50 both fail
    assert summary["latency_ms"] < 2500  # High-performance execution

    # Verify specific controls failed
    controls = data["controls"]
    assert "41" in controls
    assert controls["41"]["status"] == "FAIL"
    assert "50" in controls
    assert controls["50"]["status"] == "FAIL"

    # Verify Policies and Mandates rollups exist
    assert len(data["policies"]) > 0
    assert len(data["mandates"]) > 0


def test_api_ingest_logs_mutating_drift(client: TestClient):
    payload = {
        "provider": "AWS",
        "events": [
            # Event 1: PutRolePolicy with wildcard -> CID 50 drift
            {
                "eventID": "evt-drift-001",
                "eventTime": "2026-11-15T12:00:00Z",
                "eventName": "PutRolePolicy",
                "eventSource": "iam.amazonaws.com",
                "userIdentity": {
                    "arn": "arn:aws:iam::123456789012:user/attacker",
                },
                "sourceIPAddress": "198.51.100.23",
                "requestParameters": {
                    "roleName": "AppRole",
                    "policyName": "DriftPolicy",
                    "policyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
                    }),
                },
            },
            # Event 2: AuthorizeSecurityGroupIngress with 0.0.0.0/0 port 22 -> CID 41 drift
            {
                "eventID": "evt-drift-002",
                "eventTime": "2026-11-15T12:01:00Z",
                "eventName": "AuthorizeSecurityGroupIngress",
                "eventSource": "ec2.amazonaws.com",
                "userIdentity": {
                    "arn": "arn:aws:iam::123456789012:user/operator",
                },
                "sourceIPAddress": "203.0.113.5",
                "requestParameters": {
                    "groupId": "sg-998877",
                    "ipPermissions": {
                        "items": [
                            {
                                "fromPort": 22,
                                "toPort": 22,
                                "ipProtocol": "tcp",
                                "ipRanges": {"items": [{"cidrIp": "0.0.0.0/0"}]},
                            }
                        ]
                    },
                },
            },
        ],
    }

    response = client.post("/api/v1/cspm/ingest-logs", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["non_ai_guarantee"] is True
    assert data["processed_events"] == 2
    assert data["drift_alerts_count"] >= 2

    cids_alerted = {str(a.get("cid")) for a in data["drift_alerts"]}
    assert "50" in cids_alerted
    assert "41" in cids_alerted
