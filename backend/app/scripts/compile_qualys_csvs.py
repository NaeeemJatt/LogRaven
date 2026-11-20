#!/usr/bin/env python3
"""
LogRaven — Automated Qualys CSV-to-YAML Rule Compiler (Module 03).
Parses all 1,565 controls, 29 policies, and 38 mandates from Qualys TotalCloud exports,
synthesizes deterministic condition trees across multi-cloud evaluator families, and emits compiled YAML rules.
Zero runtime dependency on raw CSVs.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

PROVIDER_MAP = {
    "Amazon Web Service": "AWS",
    "Microsoft Azure": "AZURE",
    "Google Cloud Platform": "GCP",
    "Oracle Cloud Infrastructure": "OCI",
}

# Runtime CloudTrail Log Detection Controls (CID 18, CID 27–40)
CLOUDTRAIL_LOG_EVENT_MAP: Dict[str, List[Dict[str, Any]]] = {
    "18": [
        {"field_path": "$.userIdentity.type", "operator": "eq", "value": "Root"},
        {"field_path": "$.eventType", "operator": "neq", "value": "AwsServiceEvent"},
    ],
    "27": [
        {
            "field_path": "$.errorCode",
            "operator": "in",
            "value": ["AccessDenied", "Client.UnauthorizedOperation", "UnauthorizedOperation"],
        }
    ],
    "28": [
        {"field_path": "$.eventName", "operator": "eq", "value": "ConsoleLogin"},
        {"field_path": "$.additionalEventData.MFAUsed", "operator": "neq", "value": "Yes"},
    ],
    "29": [
        {"field_path": "$.userIdentity.type", "operator": "eq", "value": "Root"},
    ],
    "30": [
        {"field_path": "$.eventSource", "operator": "eq", "value": "iam.amazonaws.com"},
        {
            "field_path": "$.eventName",
            "operator": "in",
            "value": [
                "DeleteGroupPolicy",
                "DeleteRolePolicy",
                "DeleteUserPolicy",
                "PutGroupPolicy",
                "PutRolePolicy",
                "PutUserPolicy",
                "CreatePolicy",
                "DeletePolicy",
                "CreatePolicyVersion",
                "DeletePolicyVersion",
                "AttachRolePolicy",
                "DetachRolePolicy",
                "AttachUserPolicy",
                "DetachUserPolicy",
                "AttachGroupPolicy",
                "DetachGroupPolicy",
            ],
        },
    ],
    "31": [
        {"field_path": "$.eventSource", "operator": "eq", "value": "cloudtrail.amazonaws.com"},
        {
            "field_path": "$.eventName",
            "operator": "in",
            "value": ["CreateTrail", "UpdateTrail", "DeleteTrail", "StartLogging", "StopLogging"],
        },
    ],
    "32": [
        {"field_path": "$.eventName", "operator": "eq", "value": "ConsoleLogin"},
        {"field_path": "$.responseElements.ConsoleLogin", "operator": "eq", "value": "Failure"},
    ],
    "33": [
        {"field_path": "$.eventSource", "operator": "eq", "value": "kms.amazonaws.com"},
        {"field_path": "$.eventName", "operator": "in", "value": ["DisableKey", "ScheduleKeyDeletion"]},
    ],
    "34": [
        {"field_path": "$.eventSource", "operator": "eq", "value": "s3.amazonaws.com"},
        {
            "field_path": "$.eventName",
            "operator": "in",
            "value": [
                "PutBucketAcl",
                "PutBucketPolicy",
                "PutBucketCors",
                "PutBucketLifecycle",
                "PutBucketReplication",
                "DeleteBucketPolicy",
                "DeleteBucketCors",
                "DeleteBucketLifecycle",
                "DeleteBucketReplication",
            ],
        },
    ],
    "35": [
        {"field_path": "$.eventSource", "operator": "eq", "value": "config.amazonaws.com"},
        {
            "field_path": "$.eventName",
            "operator": "in",
            "value": [
                "StopConfigurationRecorder",
                "DeleteDeliveryChannel",
                "PutDeliveryChannel",
                "PutConfigurationRecorder",
            ],
        },
    ],
    "36": [
        {
            "field_path": "$.eventName",
            "operator": "in",
            "value": [
                "AuthorizeSecurityGroupIngress",
                "AuthorizeSecurityGroupEgress",
                "RevokeSecurityGroupIngress",
                "RevokeSecurityGroupEgress",
                "CreateSecurityGroup",
                "DeleteSecurityGroup",
            ],
        }
    ],
    "37": [
        {
            "field_path": "$.eventName",
            "operator": "in",
            "value": [
                "CreateNetworkAcl",
                "CreateNetworkAclEntry",
                "DeleteNetworkAcl",
                "DeleteNetworkAclEntry",
                "ReplaceNetworkAclEntry",
                "ReplaceNetworkAclAssociation",
            ],
        }
    ],
    "38": [
        {
            "field_path": "$.eventName",
            "operator": "in",
            "value": [
                "CreateCustomerGateway",
                "DeleteCustomerGateway",
                "AttachInternetGateway",
                "CreateInternetGateway",
                "DeleteInternetGateway",
                "DetachInternetGateway",
            ],
        }
    ],
    "39": [
        {
            "field_path": "$.eventName",
            "operator": "in",
            "value": [
                "CreateRoute",
                "CreateRouteTable",
                "ReplaceRoute",
                "ReplaceRouteTableAssociation",
                "DeleteRouteTable",
                "DeleteRoute",
            ],
        }
    ],
    "40": [
        {
            "field_path": "$.eventName",
            "operator": "in",
            "value": [
                "CreateVpc",
                "DeleteVpc",
                "ModifyVpcAttribute",
                "AcceptVpcPeeringConnection",
                "CreateVpcPeeringConnection",
            ],
        }
    ],
}


def parse_qualys_csv(filepath: str | Path, header_first_col: str) -> List[Dict[str, str]]:
    """Strips Qualys preamble (rows 0-2) and returns list of dictionaries keyed by header row."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))

    if not rows:
        return []

    header_idx = next(
        i for i, r in enumerate(rows[:10]) if r and r[0].strip().upper() == header_first_col.upper()
    )
    header = [h.strip() for h in rows[header_idx]]
    return [
        dict(zip(header, [c.strip() for c in r]))
        for r in rows[header_idx + 1:]
        if len(r) == len(header) and any(c.strip() for c in r)
    ]


def infer_conditions(
    cid: str, name: str, service: str, provider: str = "AWS"
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Infers deterministic condition rules across multi-cloud evaluator families.
    Returns: (target_source, match_logic, conditions_list)
    where a successful condition match represents a non-compliant state / VIOLATION (FAIL).
    """
    prov = provider.upper()
    svc = service.upper()
    nl = name.lower()

    # ─────────────────────────────────────────────────────────────────────────────
    # 1. AWS CloudTrail Real-Time Log Detection Controls (CIDs 18, 27–40)
    # ─────────────────────────────────────────────────────────────────────────────
    if prov == "AWS" and cid in CLOUDTRAIL_LOG_EVENT_MAP:
        return "aws_cloudtrail_log", "ALL", CLOUDTRAIL_LOG_EVENT_MAP[cid]

    # Target source resolution for configuration evaluations
    default_config_src = {
        "AWS": "aws_config_state",
        "AZURE": "azure_resource_graph",
        "GCP": "gcp_asset_inventory",
        "OCI": "oci_cloud_guard",
    }.get(prov, "aws_config_state")

    # Target source resolution for log stream evaluations
    default_log_src = {
        "AWS": "aws_cloudtrail_log",
        "AZURE": "azure_activity_log",
        "GCP": "gcp_audit_log",
        "OCI": "oci_audit_log",
    }.get(prov, "aws_cloudtrail_log")

    # Log stream rules based on service / title context
    if (prov == "AZURE" and svc in ("MONITOR", "SECURITY_CENTER") and ("activity log" in nl or "alert" in nl)) or \
       (prov == "GCP" and svc in ("LOGGING", "APIS_SERVICES") and ("audit log" in nl or "sink" in nl or "filter" in nl)) or \
       (prov == "OCI" and svc in ("EVENTS_SERVICE", "NOTIFICATION") and ("event rule" in nl or "notification topic" in nl)):
        return default_log_src, "ALL", [
            {"field_path": "$.status", "operator": "neq", "value": "ACTIVE"}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 2. Network Exposure & Open Ingress (SSH 22, RDP 3389, 0.0.0.0/0, ::/0)
    # ─────────────────────────────────────────────────────────────────────────────
    if "port 22" in nl or "ssh" in nl:
        if prov == "AWS":
            return default_config_src, "ALL", [
                {"field_path": "$.IpPermissions", "operator": "cidr_open_world", "value": 22}
            ]
        elif prov == "AZURE":
            return default_config_src, "ALL", [
                {"field_path": "$.properties.securityRules", "operator": "cidr_open_world", "value": 22}
            ]
        elif prov == "GCP":
            return default_config_src, "ALL", [
                {"field_path": "$.allowed[*].ports", "operator": "in", "value": ["22", 22]}
            ]
        elif prov == "OCI":
            return default_config_src, "ALL", [
                {"field_path": "$.ingressSecurityRules", "operator": "cidr_open_world", "value": 22}
            ]

    if "port 3389" in nl or "rdp" in nl:
        if prov == "AWS":
            return default_config_src, "ALL", [
                {"field_path": "$.IpPermissions", "operator": "cidr_open_world", "value": 3389}
            ]
        elif prov == "AZURE":
            return default_config_src, "ALL", [
                {"field_path": "$.properties.securityRules", "operator": "cidr_open_world", "value": 3389}
            ]
        elif prov == "GCP":
            return default_config_src, "ALL", [
                {"field_path": "$.allowed[*].ports", "operator": "in", "value": ["3389", 3389]}
            ]
        elif prov == "OCI":
            return default_config_src, "ALL", [
                {"field_path": "$.ingressSecurityRules", "operator": "cidr_open_world", "value": 3389}
            ]

    if "allow ingress from 0.0.0.0/0" in nl or "allow ingress from internet" in nl or "open to the world" in nl:
        if prov == "AWS":
            return default_config_src, "ALL", [
                {"field_path": "$.IpPermissions", "operator": "cidr_open_world", "value": None}
            ]
        elif prov == "AZURE":
            return default_config_src, "ALL", [
                {"field_path": "$.properties.securityRules", "operator": "cidr_open_world", "value": None}
            ]
        elif prov == "GCP":
            return default_config_src, "ALL", [
                {"field_path": "$.sourceRanges", "operator": "in", "value": ["0.0.0.0/0", "::/0"]}
            ]
        elif prov == "OCI":
            return default_config_src, "ALL", [
                {"field_path": "$.ingressSecurityRules", "operator": "cidr_open_world", "value": None}
            ]

    # Default security group / default security list
    if "default security group" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.IpPermissions", "operator": "neq", "value": []}
        ]
    if "default security list" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.isDefaultRestricted", "operator": "eq", "value": False}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 3. IAM Wildcards, Full Admin, & Root Accounts
    # ─────────────────────────────────────────────────────────────────────────────
    if "*:*" in nl or "all actions" in nl or "admin privileges" in nl:
        return default_config_src, "ANY", [
            {
                "field_path": "$.PolicyDocuments.*" if prov == "AWS" else "$.properties.rolePermissions",
                "operator": "iam_ast_wildcard",
                "value": "service_or_full_wildcard",
            }
        ]

    if "root account" in nl or "root user" in nl or "root login" in nl:
        if "access key" in nl:
            return default_config_src, "ALL", [
                {"field_path": "$.AccountAccessKeysPresent", "operator": "eq", "value": True}
            ]
        return default_config_src, "ALL", [
            {"field_path": "$.userIdentity.type", "operator": "eq", "value": "Root"}
        ]

    if "attached only to groups" in nl or "inline policy" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.UserPolicyList", "operator": "neq", "value": []}
        ]

    if "support role" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.SupportRoleExists", "operator": "eq", "value": False}
        ]

    if "access analyzer" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.AccessAnalyzerEnabled", "operator": "eq", "value": False}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 4. Multi-Factor Authentication (MFA)
    # ─────────────────────────────────────────────────────────────────────────────
    if "mfa" in nl or "multi-factor" in nl:
        field = "$.mfa_active" if prov in ("AWS", "GCP") else ("$.properties.isMfaEnabled" if prov == "AZURE" else "$.isMfaActivated")
        return default_config_src, "ALL", [
            {"field_path": field, "operator": "eq", "value": False}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 5. Password Policies (Uppercase, Lowercase, Symbol, Numeric, Length, Age)
    # ─────────────────────────────────────────────────────────────────────────────
    if "password policy" in nl or "custom iam password policy" in nl:
        if "uppercase" in nl:
            field = "$.PasswordPolicy.RequireUppercaseCharacters" if prov == "AWS" else "$.passwordPolicy.isUppercaseCharactersRequired"
            return default_config_src, "ALL", [{"field_path": field, "operator": "eq", "value": False}]
        if "lowercase" in nl:
            field = "$.PasswordPolicy.RequireLowercaseCharacters" if prov == "AWS" else "$.passwordPolicy.isLowercaseCharactersRequired"
            return default_config_src, "ALL", [{"field_path": field, "operator": "eq", "value": False}]
        if "symbol" in nl or "special character" in nl:
            field = "$.PasswordPolicy.RequireSymbols" if prov == "AWS" else "$.passwordPolicy.isSpecialCharactersRequired"
            return default_config_src, "ALL", [{"field_path": field, "operator": "eq", "value": False}]
        if "number" in nl or "numeric" in nl:
            field = "$.PasswordPolicy.RequireNumbers" if prov == "AWS" else "$.passwordPolicy.isNumericCharactersRequired"
            return default_config_src, "ALL", [{"field_path": field, "operator": "eq", "value": False}]
        if "minimum password length" in nl or "length" in nl:
            field = "$.PasswordPolicy.MinimumPasswordLength" if prov == "AWS" else "$.passwordPolicy.minimumPasswordLength"
            return default_config_src, "ALL", [{"field_path": field, "operator": "lte", "value": 14}]
        if "reuse" in nl:
            return default_config_src, "ALL", [{"field_path": "$.PasswordPolicy.PasswordReusePrevention", "operator": "lte", "value": 24}]
        if "expire" in nl or "expiration" in nl or "age" in nl:
            return default_config_src, "ALL", [{"field_path": "$.PasswordPolicy.MaxPasswordAge", "operator": "gte", "value": 90}]
        return default_config_src, "ALL", [{"field_path": "$.PasswordPolicyDefined", "operator": "eq", "value": False}]

    # ─────────────────────────────────────────────────────────────────────────────
    # 6. Encryption & Key Management (CMK, CSEK, CMEK, TDE, KMS)
    # ─────────────────────────────────────────────────────────────────────────────
    if "customer managed key" in nl or "cmk" in nl or "csek" in nl or "cmek" in nl:
        if prov == "AWS":
            return default_config_src, "ALL", [
                {"field_path": "$", "operator": "kms_cmk_encrypted", "value": False}
            ]
        elif prov == "AZURE":
            return default_config_src, "ALL", [
                {"field_path": "$.properties.encryption.keySource", "operator": "neq", "value": "Microsoft.Keyvault"}
            ]
        elif prov == "GCP":
            return default_config_src, "ALL", [
                {"field_path": "$.encryption.defaultKmsKeyName", "operator": "exists", "value": False}
            ]
        elif prov == "OCI":
            return default_config_src, "ALL", [
                {"field_path": "$.kmsKeyId", "operator": "exists", "value": False}
            ]

    if "encrypted" in nl or "encryption" in nl or "transparent data encryption" in nl:
        if prov == "AWS":
            field = "$.StorageEncrypted" if svc == "RDS" else "$.Encrypted"
            return default_config_src, "ALL", [{"field_path": field, "operator": "eq", "value": False}]
        elif prov == "AZURE":
            field = "$.properties.transparentDataEncryption.status" if svc == "AZURE_SQL" else "$.properties.encryption.services.blob.enabled"
            val = "Enabled" if svc == "AZURE_SQL" else True
            op = "neq" if svc == "AZURE_SQL" else "eq"
            return default_config_src, "ALL", [{"field_path": field, "operator": op, "value": (not val if op == "eq" else "Disabled")}]
        elif prov == "GCP":
            return default_config_src, "ALL", [{"field_path": "$.databaseEncryption.state", "operator": "neq", "value": "ENCRYPTED"}]
        elif prov == "OCI":
            return default_config_src, "ALL", [{"field_path": "$.kmsKeyId", "operator": "exists", "value": False}]

    # ─────────────────────────────────────────────────────────────────────────────
    # 7. Credential & Key Rotation Hygiene
    # ─────────────────────────────────────────────────────────────────────────────
    if "rotated" in nl or "rotation" in nl or "unused" in nl or "inactive" in nl:
        days = 45 if "45" in nl else 90
        field = "$.last_rotated_or_used" if prov == "AWS" else ("$.properties.keyRotation" if prov == "AZURE" else "$.apiKeyAgeDays")
        return default_config_src, "ALL", [
            {"field_path": field, "operator": "age_days_gte", "value": days}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 8. Exposure, Public Accessibility, & Access Controls
    # ─────────────────────────────────────────────────────────────────────────────
    if "publicly accessible" in nl or "public access" in nl or "publicly visible" in nl or "public ip" in nl:
        if prov == "AWS":
            return default_config_src, "ALL", [
                {"field_path": "$.PubliclyAccessible", "operator": "eq", "value": True}
            ]
        elif prov == "AZURE":
            return default_config_src, "ALL", [
                {"field_path": "$.properties.allowBlobPublicAccess", "operator": "eq", "value": True}
            ]
        elif prov == "GCP":
            return default_config_src, "ALL", [
                {"field_path": "$.iamConfiguration.publicAccessPrevention", "operator": "neq", "value": "enforced"}
            ]
        elif prov == "OCI":
            return default_config_src, "ALL", [
                {"field_path": "$.publicAccessType", "operator": "neq", "value": "NoPublicAccess"}
            ]

    if "block public" in nl or "block new public" in nl or "public bucket policy" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.PublicAccessBlockConfiguration.BlockPublicPolicy", "operator": "eq", "value": False}
        ]

    if "grant access to everyone" in nl or "publicly open" in nl or "grant access" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.PolicyStatus.IsPublic", "operator": "eq", "value": True}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 9. HTTPS, SSL, TLS, and Secure In-Transit Transfer
    # ─────────────────────────────────────────────────────────────────────────────
    if "https" in nl or "ssl" in nl or "tls" in nl or "secure transfer" in nl or "deny http" in nl:
        if prov == "AWS":
            return default_config_src, "ALL", [
                {"field_path": "$.ViewerProtocolPolicy", "operator": "in", "value": ["allow-all", "http-only"]}
            ]
        elif prov == "AZURE":
            field = "$.properties.httpsOnly" if svc == "APP_SERVICE" else "$.properties.supportsHttpsTrafficOnly"
            return default_config_src, "ALL", [
                {"field_path": field, "operator": "eq", "value": False}
            ]
        elif prov == "GCP":
            return default_config_src, "ALL", [
                {"field_path": "$.settings.ipConfiguration.requireSsl", "operator": "eq", "value": False}
            ]
        elif prov == "OCI":
            return default_config_src, "ALL", [
                {"field_path": "$.instanceOptions.isInTransitDataEncryptionEnabled", "operator": "eq", "value": False}
            ]

    # Client cert, HTTP 2.0, FTPS, Remote Debugging (App Service)
    if "client cert" in nl or "client certificate" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.properties.clientCertEnabled", "operator": "eq", "value": False}
        ]
    if "remote debugging" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.properties.siteConfig.remoteDebuggingEnabled", "operator": "eq", "value": True}
        ]
    if "http 2.0" in nl or "http version" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.properties.siteConfig.http20Enabled", "operator": "eq", "value": False}
        ]
    if "ftps" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.properties.siteConfig.ftpsState", "operator": "in", "value": ["AllAllowed", "Disabled"]}
        ]
    if "managed identity" in nl or "system-assigned" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.identity.type", "operator": "eq", "value": "None"}
        ]
    if "private endpoint" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.properties.privateEndpointConnections", "operator": "eq", "value": []}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 10. Audit, Logging, Monitoring, & Telemetry
    # ─────────────────────────────────────────────────────────────────────────────
    if "logging" in nl or "audit" in nl or "flow log" in nl or "diagnostic" in nl or "cloudtrail" in nl:
        if "multi-region" in nl:
            return default_config_src, "ALL", [
                {"field_path": "$.IsMultiRegionTrail", "operator": "eq", "value": False}
            ]
        if "log file validation" in nl:
            return default_config_src, "ALL", [
                {"field_path": "$.LogFileValidationEnabled", "operator": "eq", "value": False}
            ]
        if "flow log" in nl:
            return default_config_src, "ALL", [
                {"field_path": "$.FlowLogsEnabled", "operator": "eq", "value": False}
            ]
        if "cloudwatch" in nl:
            return default_config_src, "ALL", [
                {"field_path": "$.CloudWatchLogsLogGroupArn", "operator": "exists", "value": False}
            ]
        field = "$.LoggingEnabled" if prov == "AWS" else ("$.properties.diagnosticSettings.enabled" if prov == "AZURE" else "$.logging.enabled")
        return default_config_src, "ALL", [
            {"field_path": field, "operator": "eq", "value": False}
        ]

    if "log exports" in nl or "export" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.EnabledCloudwatchLogsExports", "operator": "exists", "value": False}
        ]

    if "database flag" in nl or "log_connections" in nl or "log_disconnections" in nl or "log_duration" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.settings.databaseFlags[*].value", "operator": "neq", "value": "on"}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 11. Storage Versioning, Object Lock, Uniform Bucket, & Lifecycle
    # ─────────────────────────────────────────────────────────────────────────────
    if "versioning" in nl:
        if prov == "AWS":
            return default_config_src, "ALL", [
                {"field_path": "$.Versioning.Status", "operator": "neq", "value": "Enabled"}
            ]
        elif prov == "AZURE":
            return default_config_src, "ALL", [
                {"field_path": "$.properties.isVersioningEnabled", "operator": "eq", "value": False}
            ]
        elif prov == "GCP":
            return default_config_src, "ALL", [
                {"field_path": "$.versioning.enabled", "operator": "eq", "value": False}
            ]
        elif prov == "OCI":
            return default_config_src, "ALL", [
                {"field_path": "$.versioning", "operator": "neq", "value": "Enabled"}
            ]

    if "uniform bucket" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.iamConfiguration.uniformBucketLevelAccess.enabled", "operator": "eq", "value": False}
        ]

    if "emit object events" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.objectEventsEnabled", "operator": "eq", "value": False}
        ]

    if "pre-authenticated" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.accessType", "operator": "neq", "value": "ObjectRead"}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 12. Database Posture (Multi-AZ, Backups, Deletion Protection, Minor Upgrade, Ports)
    # ─────────────────────────────────────────────────────────────────────────────
    if "multi-az" in nl or "high availability" in nl:
        field = "$.MultiAZ" if prov == "AWS" else ("$.properties.highAvailability.mode" if prov == "AZURE" else "$.settings.availabilityType")
        val = False if prov == "AWS" else ("Disabled" if prov == "AZURE" else "REGIONAL")
        op = "eq" if prov == "AWS" else ("eq" if prov == "AZURE" else "neq")
        return default_config_src, "ALL", [{"field_path": field, "operator": op, "value": val}]

    if "backup" in nl or "snapshot" in nl or "retention" in nl:
        if prov == "AWS":
            return default_config_src, "ALL", [
                {"field_path": "$.BackupRetentionPeriod", "operator": "lte", "value": 7}
            ]
        elif prov == "GCP":
            return default_config_src, "ALL", [
                {"field_path": "$.settings.backupConfiguration.enabled", "operator": "eq", "value": False}
            ]

    if "auto minor version" in nl or "automatic node upgrade" in nl or "auto upgrade" in nl:
        field = "$.AutoMinorVersionUpgrade" if prov == "AWS" else "$.management.autoUpgrade"
        return default_config_src, "ALL", [{"field_path": field, "operator": "eq", "value": False}]

    if "deletion protection" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.DeletionProtection", "operator": "eq", "value": False}
        ]

    if "default port" in nl or "standard/default port" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.Port", "operator": "in", "value": [3306, 5432, 1433, 1521, 6379, 11211]}
        ]

    if "master username" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.MasterUsername", "operator": "in", "value": ["admin", "root", "administrator", "sa", "postgres"]}
        ]

    if "iam database authentication" in nl or "iam db authentication" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.IAMDatabaseAuthenticationEnabled", "operator": "eq", "value": False}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 13. Compute & Container Posture (IMDSv2, Shielded VM, ABAC, Webhook)
    # ─────────────────────────────────────────────────────────────────────────────
    if "imds" in nl or "metadata service" in nl or "http tokens" in nl:
        field = "$.MetadataOptions.HttpTokens" if prov == "AWS" else "$.instanceOptions.isLegacyImdsEndpointsDisabled"
        val = "required" if prov == "AWS" else False
        op = "neq" if prov == "AWS" else "eq"
        return default_config_src, "ALL", [{"field_path": field, "operator": op, "value": val}]

    if "shielded" in nl or "secure boot" in nl:
        field = "$.shieldedInstanceConfig.enableSecureBoot" if prov == "GCP" else "$.instanceOptions.isSecureBootEnabled"
        return default_config_src, "ALL", [{"field_path": field, "operator": "eq", "value": False}]

    if "legacy authorization" in nl or "abac" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.legacyAbac.enabled", "operator": "eq", "value": True}
        ]

    if "network policy" in nl or "private cluster" in nl:
        field = "$.networkPolicy.enabled" if prov == "GCP" else "$.properties.networkProfile.networkPolicy"
        return default_config_src, "ALL", [{"field_path": field, "operator": "eq", "value": False}]

    if "oslogin" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.metadata.items[?(@.key=='enable-oslogin')].value", "operator": "neq", "value": "TRUE"}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 14. Key Vault / Soft Delete / Purge Protection / Defender
    # ─────────────────────────────────────────────────────────────────────────────
    if "soft delete" in nl:
        field = "$.properties.enableSoftDelete" if prov == "AZURE" else "$.deleteRetentionPolicy.enabled"
        return default_config_src, "ALL", [{"field_path": field, "operator": "eq", "value": False}]

    if "purge protection" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.properties.enablePurgeProtection", "operator": "eq", "value": False}
        ]

    if "defender" in nl or "security center" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.properties.pricingTier", "operator": "neq", "value": "Standard"}
        ]

    if "tag" in nl or "tagged" in nl or "untagged" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.tags", "operator": "exists", "value": False}
        ]

    if "tracing" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.TracingConfig.Mode", "operator": "neq", "value": "Active"}
        ]

    if "cloud guard" in nl:
        return default_config_src, "ALL", [
            {"field_path": "$.status", "operator": "neq", "value": "ENABLED"}
        ]

    # ─────────────────────────────────────────────────────────────────────────────
    # 15. Default Fallback Evaluation Logic
    # ─────────────────────────────────────────────────────────────────────────────
    return default_config_src, "ALL", [
        {"field_path": f"$.controls.cid_{cid}_compliant", "operator": "eq", "value": False}
    ]


def infer_criticality(raw_crit: str, name: str) -> str:
    """Elevates acute crown-jewel breach vectors (root MFA, 0.0.0.0 ingress, public storage) to CRITICAL."""
    crit = raw_crit.upper().strip()
    if crit == "HIGH":
        nl = name.lower()
        if any(kw in nl for kw in [
            "root user", "root account", "multi-factor authentication", "(mfa)",
            "0.0.0.0/0", "::/0", "publicly accessible", "public accessibility",
            "anonymous access", "public access", "public bucket", "port 22", "port 3389",
            "unrestricted ingress", "clear text", "unencrypted credentials"
        ]):
            return "CRITICAL"
    return crit


def assign_policies(
    provider: str, service: str, exec_type: str, all_policies: List[Dict[str, str]]
) -> List[str]:
    """Maps a control to applicable policies based on provider, service, and title matching."""
    matched = []
    prov_upper = provider.upper()

    for p in all_policies:
        if p.get("PROVIDER", "").upper() != prov_upper:
            continue
        title = p["POLICY TITLE"]
        tl = title.lower()

        if (
            "best practices" in tl
            and "database" not in tl
            and "ai " not in tl
            and "lambda" not in tl
            and "iam" not in tl
            and "function" not in tl
            and "sql" not in tl
            and "kubernetes" not in tl
            and "infrastructure as code" not in tl
        ):
            matched.append(title)
        elif "foundations" in tl or "foundation" in tl:
            matched.append(title)
        elif service in (
            "RDS", "DYNAMO_DB", "NEPTUNE_DB", "REDSHIFT", "DOCUMENT_DB",
            "AZURE_SQL", "COSMOS_DB", "SQL", "DATABASE"
        ) and ("database" in tl or "sql" in tl):
            matched.append(title)
        elif service in (
            "S3", "EFS", "FILE_SYSTEM", "S3_GLACIER", "STORAGE_ACCOUNT",
            "DISK", "STORAGE"
        ) and "storage" in tl:
            matched.append(title)
        elif service in (
            "EC2", "ECS", "EKS", "LAMBDA", "BATCH", "VIRTUAL_MACHINE",
            "KUBERNETES_SERVICE", "COMPUTE_ENGINE", "KUBERNETES", "COMPUTE"
        ) and ("compute" in tl or "kubernetes" in tl or "lambda" in tl or "function" in tl):
            matched.append(title)
        elif service in ("IAM", "AZURE_AD") and "identity" in tl:
            matched.append(title)
        elif service in (
            "BEDROCK", "SAGEMAKER", "COMPREHEND", "LEX", "KENDRA",
            "COGNITIVE_SERVICES", "WORKBENCH", "COLAB_ENTERPRISE"
        ) and "ai service" in tl:
            matched.append(title)
        elif "Build" in exec_type and "infrastructure as code" in tl:
            matched.append(title)

    return sorted(set(matched))


def compile_all(catalog_dir: str | Path, out_rules_dir: str | Path) -> Dict[str, Any]:
    """Compiles all 4 control CSVs, policies, and mandates into self-contained YAML rule definition files."""
    cat_dir = Path(catalog_dir)
    out_dir = Path(out_rules_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    policies = parse_qualys_csv(cat_dir / "policies.csv", "POLICY TITLE")
    mandates = parse_qualys_csv(cat_dir / "mandates.csv", "NAME")
    mandate_names = [m["NAME"] for m in mandates]

    csv_files = {
        "aws": "controls_aws.csv",
        "azure": "controls_azure.csv",
        "gcp": "controls_gcp.csv",
        "oci": "controls_oci.csv",
    }

    results: Dict[str, Any] = {
        "total_rules": 0,
        "files_compiled": {},
        "policies_count": len(policies),
        "mandates_count": len(mandates),
    }

    for short_prov, fname in csv_files.items():
        raw_controls = parse_qualys_csv(cat_dir / fname, "CID")
        compiled_rules = []

        for row in raw_controls:
            cid = row["CID"]
            prov = PROVIDER_MAP.get(row.get("PLATFORM", ""), short_prov.upper())
            svc = row.get("SERVICE", "GENERAL")
            exec_t = row.get("EXECUTION TYPE", "Run Time")
            target_src, logic, conds = infer_conditions(cid, row.get("CONTROL NAME", ""), svc, provider=prov)

            rule_entry = {
                "rule_id": f"QUALYS-{prov}-CID-{cid}",
                "cid": cid,
                "title": row.get("CONTROL NAME", ""),
                "provider": prov,
                "service": svc,
                "execution_type": exec_t,
                "criticality": infer_criticality(row.get("CRITICALITY", "HIGH"), row.get("CONTROL NAME", "")),
                "target_source": target_src,
                "match_logic": logic,
                "conditions": conds,
                "policies": assign_policies(prov, svc, exec_t, policies),
                "mandates": mandate_names,
            }
            compiled_rules.append(rule_entry)

        out_path = out_dir / f"cspm_{short_prov}.yaml"
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump({"rules": compiled_rules}, f, sort_keys=False, allow_unicode=True)

        results["files_compiled"][short_prov] = {
            "path": str(out_path),
            "count": len(compiled_rules),
        }
        results["total_rules"] += len(compiled_rules)
        print(f"Compiled {len(compiled_rules):<4} rules -> {out_path}")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="LogRaven Qualys CSV to YAML Compiler")
    default_cat = Path(__file__).resolve().parent.parent / "data" / "csv_catalog"
    default_out = Path(__file__).resolve().parent.parent / "data" / "rules"

    parser.add_argument("--catalog-dir", default=str(default_cat), help="Path to csv_catalog directory")
    parser.add_argument("--out-rules-dir", default=str(default_out), help="Path to output rules directory")
    args = parser.parse_args()

    print("=== LogRaven Qualys CSV Compiler (Module 03) ===")
    print(f"Catalog Source: {args.catalog_dir}")
    print(f"Rules Target:   {args.out_rules_dir}")

    summary = compile_all(args.catalog_dir, args.out_rules_dir)

    print("\n--- Compilation Results ---")
    print(f"Total Rules Compiled: {summary['total_rules']} / 1565")
    for prov, info in summary["files_compiled"].items():
        print(f"  [{prov.upper()}] {info['count']} rules in {info['path']}")

    if summary["total_rules"] == 1565:
        print("\n>>> COMPILATION STATUS: SUCCESS (All 1,565 Rules Compiled) <<<")
        return 0
    else:
        print(f"\n>>> COMPILATION STATUS: FAILED (Expected 1565, got {summary['total_rules']}) <<<")
        return 1


if __name__ == "__main__":
    sys.exit(main())
