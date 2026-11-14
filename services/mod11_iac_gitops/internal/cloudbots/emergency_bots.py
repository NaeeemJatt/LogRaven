"""Serverless CloudBots for automated runtime emergency remediations (PRD-MOD-11)."""

from typing import Any, Dict


class CloudBotS3BlockPublic:
    """Auto-enables S3 PublicAccessBlock on unencrypted / exposed buckets."""

    BOT_ID = "bot-s3-block-public"

    @classmethod
    def generate_remediation_action(cls, bucket_name: str) -> Dict[str, Any]:
        return {
            "bot_id": cls.BOT_ID,
            "action": "s3:PutPublicAccessBlock",
            "resource": bucket_name,
            "parameters": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
            "cli_command": (
                f"aws s3control put-public-access-block --account-id <ACCOUNT_ID> "
                f"--public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,"
                f"BlockPublicPolicy=true,RestrictPublicBuckets=true"
            ),
        }


class CloudBotSGRevokeSSH:
    """Auto-revokes 0.0.0.0/0 ingress on port 22 across security groups."""

    BOT_ID = "bot-sg-revoke-ssh"

    @classmethod
    def generate_remediation_action(cls, group_id: str) -> Dict[str, Any]:
        return {
            "bot_id": cls.BOT_ID,
            "action": "ec2:RevokeSecurityGroupIngress",
            "resource": group_id,
            "parameters": {
                "GroupId": group_id,
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "CidrIp": "0.0.0.0/0",
            },
            "cli_command": f"aws ec2 revoke-security-group-ingress --group-id {group_id} --protocol tcp --port 22 --cidr 0.0.0.0/0",
        }


class CloudBotEnableKMSRotation:
    """Auto-enables KMS annual key rotation."""

    BOT_ID = "bot-enable-kms-rotation"

    @classmethod
    def generate_remediation_action(cls, key_id: str) -> Dict[str, Any]:
        return {
            "bot_id": cls.BOT_ID,
            "action": "kms:EnableKeyRotation",
            "resource": key_id,
            "parameters": {"KeyId": key_id},
            "cli_command": f"aws kms enable-key-rotation --key-id {key_id}",
        }
