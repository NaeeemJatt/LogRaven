# LogRaven — SOC 2 Compliance Constants

from __future__ import annotations

OFF_HOURS_UTC_START = 6
OFF_HOURS_UTC_END = 22

CLOUDTRAIL_EVENT_NAMES: frozenset[str] = frozenset({
    "ConsoleLogin",
    "AssumeRole",
    "CreateUser",
    "DeleteUser",
    "AttachUserPolicy",
    "DetachUserPolicy",
    "AttachRolePolicy",
    "DetachRolePolicy",
    "CreateAccessKey",
    "DeleteAccessKey",
    "PutBucketPolicy",
    "CreateBucket",
    "DeleteBucket",
    "AuthorizeSecurityGroupIngress",
    "RunInstances",
    "TerminateInstances",
})

# Event name -> sanitizer category
EVENT_NAME_TO_CATEGORY: dict[str, str] = {
    "ConsoleLogin": "login",
    "AssumeRole": "privilege",
    "AttachUserPolicy": "policy",
    "DetachUserPolicy": "policy",
    "AttachRolePolicy": "policy",
    "DetachRolePolicy": "policy",
    "PutBucketPolicy": "policy",
    "AuthorizeSecurityGroupIngress": "policy",
    "CreateUser": "resource_creation",
    "CreateBucket": "resource_creation",
    "RunInstances": "resource_creation",
    "DeleteUser": "resource_deletion",
    "DeleteBucket": "resource_deletion",
    "TerminateInstances": "resource_deletion",
    "DeleteAccessKey": "resource_deletion",
    "CreateAccessKey": "access_key",
}

RESOURCE_CREATION_EVENTS = frozenset(
    name for name, cat in EVENT_NAME_TO_CATEGORY.items() if cat == "resource_creation"
)
RESOURCE_DELETION_EVENTS = frozenset(
    name for name, cat in EVENT_NAME_TO_CATEGORY.items() if cat == "resource_deletion"
)

SOC2_CONTROLS: list[dict[str, str]] = [
    {
        "control_id": "CC6.1",
        "control_name": "Logical access security software, infrastructure, and architectures",
    },
    {
        "control_id": "CC6.2",
        "control_name": "New internal and external users are registered and authorized",
    },
    {
        "control_id": "CC6.3",
        "control_name": "Internal and external users are removed when no longer authorized",
    },
    {
        "control_id": "CC6.6",
        "control_name": "Logical access restrictions to systems used to protect against threats from persons acting outside system boundaries",
    },
    {
        "control_id": "CC6.7",
        "control_name": "Transmission, movement, and removal of information is restricted to authorized users",
    },
    {
        "control_id": "CC6.8",
        "control_name": "Controls to prevent or detect and act upon the introduction of unauthorized or malicious software",
    },
    {
        "control_id": "CC7.1",
        "control_name": "Vulnerability management program",
    },
    {
        "control_id": "CC7.2",
        "control_name": "System components are monitored to detect anomalies",
    },
    {
        "control_id": "CC7.3",
        "control_name": "Evaluated security events to determine if they are security incidents",
    },
    {
        "control_id": "CC7.4",
        "control_name": "Identified security incidents are contained and remediated",
    },
    {
        "control_id": "CC7.5",
        "control_name": "Identified vulnerabilities are remediated",
    },
]

SOC2_CONTROL_IDS: frozenset[str] = frozenset(c["control_id"] for c in SOC2_CONTROLS)
