"""Deep configuration enricher for AWS EC2 Instances."""

import inspect
from typing import Any, Dict


class EC2Enricher:
    """Enriches EC2 instance inventory with IMDSv2, EBS encryption, and network interfaces."""

    @staticmethod
    async def enrich_instance(ec2_client: Any, instance_raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes and extracts security configuration from raw EC2 description."""
        instance_id = instance_raw.get("InstanceId", "")
        metadata_options = instance_raw.get("MetadataOptions", {})

        imdsv2_required = metadata_options.get("HttpTokens") == "required"
        security_groups = [
            {"group_id": sg.get("GroupId"), "group_name": sg.get("GroupName")}
            for sg in instance_raw.get("SecurityGroups", [])
        ]

        return {
            "instance_id": instance_id,
            "instance_type": instance_raw.get("InstanceType"),
            "state": instance_raw.get("State", {}).get("Name"),
            "subnet_id": instance_raw.get("SubnetId"),
            "vpc_id": instance_raw.get("VpcId"),
            "public_ip": instance_raw.get("PublicIpAddress"),
            "private_ip": instance_raw.get("PrivateIpAddress"),
            "imdsv2_required": imdsv2_required,
            "security_groups": security_groups,
            "ebs_optimized": instance_raw.get("EbsOptimized", False),
        }

