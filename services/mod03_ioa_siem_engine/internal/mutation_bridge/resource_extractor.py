"""Mutation Bridge: Extracts mutating resources from CloudTrail/Activity events and enqueues priority re-crawls."""

import logging
from typing import Any, Dict, Optional
import uuid

from services.mod02_asset_crawler.internal.normalizer.urn_builder import build_urn

logger = logging.getLogger(__name__)

# Set of mutating cloud API operations requiring immediate posture re-assessment
MUTATING_CLOUD_OPERATIONS = {
    # AWS EC2 & VPC
    "AuthorizeSecurityGroupIngress",
    "AuthorizeSecurityGroupEgress",
    "RevokeSecurityGroupIngress",
    "RevokeSecurityGroupEgress",
    "ModifySecurityGroupRules",
    "CreateSecurityGroup",
    "RunInstances",
    "TerminateInstances",
    "StopInstances",
    # AWS S3
    "PutBucketAcl",
    "PutBucketPolicy",
    "DeleteBucketPolicy",
    "PutBucketPublicAccessBlock",
    "PutBucketEncryption",
    "CreateBucket",
    "DeleteBucket",
    # AWS IAM
    "AttachRolePolicy",
    "DetachRolePolicy",
    "PutRolePolicy",
    "AttachUserPolicy",
    "PutUserPolicy",
    "CreateUser",
    "CreateRole",
    # Azure
    "Microsoft.Authorization/roleAssignments/write",
    "Microsoft.Authorization/roleAssignments/delete",
    "Microsoft.Network/networkSecurityGroups/securityRules/write",
    # GCP
    "google.iam.v1.IAMPolicy.SetIamPolicy",
    "v1.compute.instances.insert",
    "v1.compute.firewalls.insert",
    "v1.compute.firewalls.patch",
}


class MutationBridge:
    """Detects mutating events and dispatches priority single-resource discovery jobs."""

    def __init__(self, crawler_queue=None):
        self.crawler_queue = crawler_queue
        self.enqueued_jobs = []

    def is_mutating_event(self, event_name: str) -> bool:
        """Checks if event alters infrastructure configuration or security boundary."""
        if not event_name:
            return False
        clean = event_name.split(":")[-1]
        return clean in MUTATING_CLOUD_OPERATIONS or event_name in MUTATING_CLOUD_OPERATIONS

    def extract_and_enqueue(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """If event is mutating, extracts resource identifier and enqueues high-priority crawler job."""
        event_name = event.get("event_name") or event.get("eventName") or ""
        if not self.is_mutating_event(event_name):
            return None

        provider = event.get("provider", "aws").lower()
        account_id = str(
            event.get("account_id")
            or event.get("recipientAccountId")
            or (event.get("userIdentity", {}).get("accountId") if isinstance(event.get("userIdentity"), dict) else None)
            or "unknown-account"
        )
        region = str(event.get("region") or event.get("awsRegion") or "us-east-1")

        target_urn = event.get("target_resource_urn")
        resource_id = None
        service = "cloud"
        res_type = "resource"

        raw = event.get("raw_event") or event
        params = raw.get("requestParameters") or {}

        # S3
        if "bucketName" in params:
            service = "s3"
            res_type = "aws_s3_bucket"
            resource_id = params["bucketName"]
        # EC2 Security Group
        elif "groupId" in params:
            service = "ec2"
            res_type = "aws_security_group"
            resource_id = params["groupId"]
        elif "roleName" in params:
            service = "iam"
            res_type = "aws_iam_role"
            resource_id = params["roleName"]
        elif "functionName" in params:
            service = "lambda"
            res_type = "aws_lambda_function"
            resource_id = params["functionName"]
        elif target_urn and target_urn.startswith("urn:lograven:"):
            # URN already formed
            resource_id = target_urn.split("/")[-1]
        else:
            resource_id = f"res-{uuid.uuid4().hex[:8]}"

        if not target_urn or not target_urn.startswith("urn:lograven:"):
            target_urn = build_urn(provider, account_id, region, service, res_type, resource_id)

        job = {
            "job_id": f"crawl-pri-{uuid.uuid4().hex[:12]}",
            "priority": "HIGH",
            "provider": provider,
            "account_id": account_id,
            "region": region,
            "target_urn": target_urn,
            "resource_id": resource_id,
            "trigger_event": event_name,
            "status": "ENQUEUED",
        }

        self.enqueued_jobs.append(job)
        if self.crawler_queue is not None:
            try:
                self.crawler_queue.put_nowait(job)
            except Exception as e:
                logger.warning(f"Failed to push crawl job to queue: {e}")

        logger.info(f"Priority re-crawl enqueued: {job['job_id']} for {target_urn}")
        return job
