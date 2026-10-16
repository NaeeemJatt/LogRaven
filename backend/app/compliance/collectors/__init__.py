# LogRaven — Compliance evidence collectors
#
# Multi-cloud collector architecture supporting AWS, Google Cloud Platform (GCP),
# and Microsoft Azure.

from app.compliance.collectors.base import BaseCloudCollector
from app.compliance.collectors.aws_extended import collect_extended_evidence
from app.compliance.collectors.gcp import GCPCollector
from app.compliance.collectors.azure import AzureCollector
from app.compliance.collectors.factory import AWSCollector, get_collector

__all__ = [
    "BaseCloudCollector",
    "collect_extended_evidence",
    "GCPCollector",
    "AzureCollector",
    "AWSCollector",
    "get_collector",
]
