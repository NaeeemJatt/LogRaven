# LogRaven — Multi-Cloud Collector Factory
#
# Returns the appropriate collector implementation (AWS, GCP, Azure) based on
# the cloud provider registered on the CloudAccount model.

from __future__ import annotations

from typing import Any

from app.compliance.collectors.base import BaseCloudCollector
from app.compliance.collectors.gcp import GCPCollector
from app.compliance.collectors.azure import AzureCollector


class AWSCollector(BaseCloudCollector):
    """Wrapper around AWS collection pipeline."""

    def verify_credentials(self, credentials: dict[str, Any]) -> dict[str, Any]:
        role_arn = credentials.get("role_arn")
        if not role_arn:
            return {"healthy": False, "error": "Missing AWS Role ARN", "account_id": None}

        account_id = None
        arn_parts = role_arn.split(":")
        if len(arn_parts) >= 5 and arn_parts[4].isdigit():
            account_id = arn_parts[4]

        return {
            "healthy": True,
            "error": None,
            "account_id": account_id,
            "provider": "aws",
        }

    def collect_evidence(
        self,
        credentials: dict[str, Any],
        start_date: Any,
        end_date: Any,
    ) -> dict[str, Any]:
        # AWS uses the existing boto3 collection in aws_collector and aws_extended
        from app.compliance.aws_collector import (
            get_aws_session,
            get_cloudtrail_events,
            get_iam_summary,
            get_guardduty_findings,
        )
        from app.compliance.collectors.aws_extended import collect_extended_evidence

        role_arn = credentials.get("role_arn", "")
        session = get_aws_session(role_arn)
        cloudtrail_events = get_cloudtrail_events(session, start_date, end_date)
        iam_summary = get_iam_summary(session)
        guardduty_findings = get_guardduty_findings(session)
        extended = collect_extended_evidence(session)

        return {
            "provider": "aws",
            "cloudtrail_events": cloudtrail_events,
            "iam_summary": iam_summary,
            "guardduty_findings": guardduty_findings,
            "extended": extended,
        }


def get_collector(provider: str) -> BaseCloudCollector:
    """Return the collector for the given cloud provider ('aws', 'gcp', 'azure')."""
    prov = (provider or "aws").lower().strip()
    if prov == "gcp":
        return GCPCollector()
    elif prov == "azure":
        return AzureCollector()
    elif prov == "aws":
        return AWSCollector()
    else:
        raise ValueError(f"Unsupported cloud provider: '{provider}'")
