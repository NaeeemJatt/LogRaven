"""Curated repository of actionable remediation guides for cloud security and compliance."""

from __future__ import annotations

from typing import Iterable
from app.compliance.remediation.schemas import RemediationGuide

# ═════════════════════════════════════════════════════════════════════════════
# Curated Guides by Signal Key
# ═════════════════════════════════════════════════════════════════════════════

SIGNAL_REMEDIATION_CATALOG: dict[str, RemediationGuide] = {
    "s3_public_access_blocked": RemediationGuide(
        control_id="s3_public_access_blocked",
        title="Enable Account-Level S3 Public Access Block",
        threat_rationale="Unrestricted S3 buckets are the leading cause of massive data exfiltration events in AWS environments.",
        estimated_time_minutes=3,
        console_steps=[
            "Open the Amazon S3 console at https://console.aws.amazon.com/s3/.",
            "In the left navigation pane, choose 'Block Public Access (account settings)'.",
            "Choose 'Edit'.",
            "Select 'Block all public access' (check all four boxes).",
            "Choose 'Save changes' and type 'confirm' in the dialog box.",
        ],
        aws_cli_command=(
            "aws s3control put-public-access-block \\\n"
            "  --account-id $(aws sts get-caller-identity --query Account --output text) \\\n"
            '  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"'
        ),
        terraform_snippet=(
            'resource "aws_s3_account_public_access_block" "account_wide" {\n'
            "  block_public_acls       = true\n"
            "  block_public_policy     = true\n"
            "  ignore_public_acls      = true\n"
            "  restrict_public_buckets = true\n"
            "}"
        ),
        verification_command=(
            "aws s3control get-public-access-block \\\n"
            "  --account-id $(aws sts get-caller-identity --query Account --output text)"
        ),
    ),

    "iam_root_mfa_enabled": RemediationGuide(
        control_id="iam_root_mfa_enabled",
        title="Activate Multi-Factor Authentication (MFA) on AWS Root Account",
        threat_rationale="The root user has unrestricted, irrevocable access to all account resources. Compromise bypasses all IAM boundary controls.",
        estimated_time_minutes=5,
        console_steps=[
            "Sign in to the AWS Management Console as the root user.",
            "In the upper right corner, choose your account name, and then choose 'Security credentials'.",
            "In the 'Multi-factor authentication (MFA)' section, choose 'Assign MFA device'.",
            "Enter a device name (e.g., 'Root-Authenticator') and select 'Authenticator app' or 'FIDO2 security key'.",
            "Follow on-screen instructions to scan the QR code and submit two consecutive 6-digit codes.",
            "Choose 'Add MFA'.",
        ],
        aws_cli_command="# Note: AWS Root MFA cannot be configured via API/CLI for security reasons. Complete via AWS Management Console.",
        terraform_snippet="# Note: Root user credentials cannot be managed by Terraform. Configure directly in AWS Console.",
        verification_command=(
            'aws iam get-account-summary --query "SummaryMap.AccountMFAEnabled" --output json'
        ),
    ),

    "iam_mfa_enforcement_rate": RemediationGuide(
        control_id="iam_mfa_enforcement_rate",
        title="Enforce Multi-Factor Authentication (MFA) for All IAM Users",
        threat_rationale="Single-factor authentication allows password spraying and credential stuffing to yield immediate administrative console access.",
        estimated_time_minutes=10,
        console_steps=[
            "Sign in to the IAM Console at https://console.aws.amazon.com/iam/.",
            "In the navigation pane, choose 'Policies' and then 'Create policy'.",
            "Select the JSON tab and paste an IAM policy requiring MFA for API and console access.",
            "Name the policy 'EnforceMFAPolicy' and create it.",
            "Attach 'EnforceMFAPolicy' to all IAM groups containing human console users.",
        ],
        aws_cli_command=(
            "aws iam create-policy \\\n"
            "  --policy-name BlockActionsWithoutMFA \\\n"
            '  --policy-document \'{"Version":"2012-10-17","Statement":[{"Sid":"BlockNonMFA","Effect":"Deny","NotAction":["iam:CreateVirtualMFADevice","iam:EnableMFADevice","iam:GetUser","iam:ListMFADevices","iam:ResyncMFADevice"],"Resource":"*","Condition":{"BoolIfExists":{"aws:MultiFactorAuthPresent":"false"}}}]}\''
        ),
        terraform_snippet=(
            'resource "aws_iam_policy" "enforce_mfa" {\n'
            '  name        = "EnforceMFA"\n'
            '  description = "Denies all actions except self-MFA registration unless MFA is present"\n'
            "  policy = jsonencode({\n"
            '    Version = "2012-10-17"\n'
            "    Statement = [{\n"
            '      Sid       = "BlockActionsWithoutMFA"\n'
            '      Effect    = "Deny"\n'
            '      NotAction = [\n'
            '        "iam:CreateVirtualMFADevice",\n'
            '        "iam:EnableMFADevice",\n'
            '        "iam:GetUser",\n'
            '        "iam:ListMFADevices",\n'
            '        "iam:ResyncMFADevice"\n'
            "      ]\n"
            '      Resource = "*"\n'
            '      Condition = {\n'
            '        BoolIfExists = { "aws:MultiFactorAuthPresent" = "false" }\n'
            "      }\n"
            "    }]\n"
            "  })\n"
            "}"
        ),
        verification_command=(
            "aws iam get-account-summary --query 'SummaryMap.{Total: Users, MFA: UsersWithMFA}'"
        ),
    ),

    "ebs_default_encryption": RemediationGuide(
        control_id="ebs_default_encryption",
        title="Enable Account-Level EBS Default Encryption",
        threat_rationale="Unencrypted EBS volumes risk raw physical data exposure if snapshot volumes or drives are improperly detached or shared.",
        estimated_time_minutes=2,
        console_steps=[
            "Open the Amazon EC2 console at https://console.aws.amazon.com/ec2/.",
            "In the navigation pane, under 'Settings', select 'Data protection and security'.",
            "In the 'EBS encryption' section, choose 'Manage'.",
            "Select 'Always encrypt new EBS volumes'.",
            "Choose 'Update EBS encryption'.",
        ],
        aws_cli_command="aws ec2 enable-ebs-encryption-by-default",
        terraform_snippet=(
            'resource "aws_ebs_encryption_by_default" "enabled" {\n'
            "  enabled = true\n"
            "}"
        ),
        verification_command="aws ec2 get-ebs-encryption-by-default",
    ),

    "rds_encryption_rate": RemediationGuide(
        control_id="rds_encryption_rate",
        title="Encrypt All Relational Database Service (RDS) Instances at Rest",
        threat_rationale="Unencrypted databases store critical business entities, customer credentials, and PII in plaintext on disk.",
        estimated_time_minutes=15,
        console_steps=[
            "Open the Amazon RDS console at https://console.aws.amazon.com/rds/.",
            "Select the target unencrypted DB instance and choose 'Take snapshot'.",
            "Once snapshot completes, select it and choose 'Actions' -> 'Copy snapshot'.",
            "In the copy settings, check 'Enable encryption' and select an AWS KMS key.",
            "Choose 'Restore snapshot' to launch an encrypted replacement database instance.",
            "Update application connection strings to the new database endpoint.",
        ],
        aws_cli_command=(
            "aws rds copy-db-snapshot \\\n"
            "  --source-db-snapshot-identifier <SOURCE_SNAPSHOT_ID> \\\n"
            "  --target-db-snapshot-identifier <ENCRYPTED_SNAPSHOT_ID> \\\n"
            "  --kms-key-id alias/aws/rds"
        ),
        terraform_snippet=(
            'resource "aws_db_instance" "database" {\n'
            '  identifier          = "production-db"\n'
            "  storage_encrypted   = true\n"
            '  kms_key_id          = "arn:aws:kms:region:account:key/id"\n'
            "  # ... remaining DB parameters ...\n"
            "}"
        ),
        verification_command=(
            "aws rds describe-db-instances --query 'DBInstances[*].[DBInstanceIdentifier, StorageEncrypted]'"
        ),
    ),

    "cloudtrail_log_validation": RemediationGuide(
        control_id="cloudtrail_log_validation",
        title="Enable CloudTrail Log File Integrity Validation",
        threat_rationale="Without cryptographic digest validation, attackers can tamper with, modify, or delete historical audit records without detection.",
        estimated_time_minutes=3,
        console_steps=[
            "Open the CloudTrail console at https://console.aws.amazon.com/cloudtrail/.",
            "In the navigation pane, choose 'Trails'.",
            "Select the active trail.",
            "Under 'General details', choose 'Edit'.",
            "Under 'Log file validation', select 'Enabled'.",
            "Choose 'Save changes'.",
        ],
        aws_cli_command=(
            "aws cloudtrail update-trail \\\n"
            "  --name <TRAIL_NAME> \\\n"
            "  --enable-log-file-validation"
        ),
        terraform_snippet=(
            'resource "aws_cloudtrail" "main" {\n'
            '  name                          = "audit-trail"\n'
            '  s3_bucket_name                = "company-audit-logs"\n'
            "  enable_log_file_validation    = true\n"
            "  is_multi_region_trail         = true\n"
            "}"
        ),
        verification_command=(
            "aws cloudtrail describe-trails --query 'trailList[*].[Name, LogFileValidationEnabled]'"
        ),
    ),

    "cloudtrail_multiregion": RemediationGuide(
        control_id="cloudtrail_multiregion",
        title="Configure Multi-Region CloudTrail Trail",
        threat_rationale="Attacking activity frequently takes place in inactive or non-default regions to avoid single-region monitoring detection.",
        estimated_time_minutes=3,
        console_steps=[
            "Open CloudTrail console at https://console.aws.amazon.com/cloudtrail/.",
            "Select your primary trail.",
            "Under 'General details', choose 'Edit'.",
            "Set 'Multi-region trail' to 'Yes'.",
            "Choose 'Save changes'.",
        ],
        aws_cli_command=(
            "aws cloudtrail update-trail \\\n"
            "  --name <TRAIL_NAME> \\\n"
            "  --is-multi-region-trail"
        ),
        terraform_snippet=(
            'resource "aws_cloudtrail" "global" {\n'
            '  name                  = "global-compliance-trail"\n'
            '  s3_bucket_name        = "compliance-logs-vault"\n'
            "  is_multi_region_trail = true\n"
            "  include_global_service_events = true\n"
            "}"
        ),
        verification_command=(
            "aws cloudtrail describe-trails --query 'trailList[*].[Name, IsMultiRegionTrail]'"
        ),
    ),

    "cloudtrail_encrypted": RemediationGuide(
        control_id="cloudtrail_encrypted",
        title="Encrypt CloudTrail Log Files with Customer-Managed KMS Key (SSE-KMS)",
        threat_rationale="Server-side encryption using KMS CMKs prevents unauthorized cross-account log reads even if S3 bucket policy is misconfigured.",
        estimated_time_minutes=8,
        console_steps=[
            "Open CloudTrail console and choose 'Trails'.",
            "Select your active trail and choose 'Edit' under General details.",
            "In 'Log file SSE-KMS encryption', select 'Enabled'.",
            "Choose 'Existing AWS KMS key' and select your compliance KMS key.",
            "Choose 'Save changes'.",
        ],
        aws_cli_command=(
            "aws cloudtrail update-trail \\\n"
            "  --name <TRAIL_NAME> \\\n"
            "  --kms-key-id <KMS_KEY_ARN>"
        ),
        terraform_snippet=(
            'resource "aws_cloudtrail" "encrypted_trail" {\n'
            '  name           = "audited-trail"\n'
            '  s3_bucket_name = "audited-trail-logs"\n'
            "  kms_key_id     = aws_kms_key.trail_key.arn\n"
            "}"
        ),
        verification_command=(
            "aws cloudtrail describe-trails --query 'trailList[*].[Name, KmsKeyId]'"
        ),
    ),

    "open_security_groups": RemediationGuide(
        control_id="open_security_groups",
        title="Restrict Ingress to Sensitive Ports from 0.0.0.0/0",
        threat_rationale="Exposing management ports (22 SSH, 3389 RDP, 5432 Postgres, 3306 MySQL) to the public internet enables brute force and remote exploitation.",
        estimated_time_minutes=5,
        console_steps=[
            "Open the Amazon EC2 console at https://console.aws.amazon.com/ec2/.",
            "In the navigation pane, choose 'Security Groups'.",
            "Filter for security groups with inbound rules allowing '0.0.0.0/0' on port 22 or 3389.",
            "Select the security group and choose 'Actions' -> 'Edit inbound rules'.",
            "Change the source from 'Anywhere-IPv4 (0.0.0.0/0)' to your corporate VPN CIDR or a bastion security group.",
            "Choose 'Save rules'.",
        ],
        aws_cli_command=(
            "aws ec2 revoke-security-group-ingress \\\n"
            "  --group-id <SECURITY_GROUP_ID> \\\n"
            "  --protocol tcp --port 22 --cidr 0.0.0.0/0"
        ),
        terraform_snippet=(
            'resource "aws_security_group_rule" "restricted_ssh" {\n'
            '  type              = "ingress"\n'
            "  from_port         = 22\n"
            "  to_port           = 22\n"
            '  protocol          = "tcp"\n'
            '  cidr_blocks       = ["10.0.0.0/16"] # Corporate VPN CIDR only\n'
            "  security_group_id = aws_security_group.workloads.id\n"
            "}"
        ),
        verification_command=(
            "aws ec2 describe-security-groups \\\n"
            '  --filters "Name=ip-permission.cidr,Values=0.0.0.0/0" "Name=ip-permission.from-port,Values=22" \\\n'
            "  --query 'SecurityGroups[*].[GroupId, GroupName]'"
        ),
    ),

    "default_sg_restricted": RemediationGuide(
        control_id="default_sg_restricted",
        title="Restrict Default Security Groups to Deny All Traffic",
        threat_rationale="Default VPC security groups should not permit inbound or outbound traffic, preventing unintended communications if accidentally attached.",
        estimated_time_minutes=3,
        console_steps=[
            "Open the Amazon VPC console at https://console.aws.amazon.com/vpc/.",
            "In the navigation pane, choose 'Security groups'.",
            "Select the 'default' security group for each VPC.",
            "Choose 'Actions' -> 'Edit inbound rules' and delete all rules.",
            "Choose 'Actions' -> 'Edit outbound rules' and delete all rules.",
        ],
        aws_cli_command=(
            "# Revoke all default ingress:\n"
            "aws ec2 revoke-security-group-ingress --group-id <DEFAULT_SG_ID> --protocol all --cidr 0.0.0.0/0\n"
            "# Revoke all default egress:\n"
            "aws ec2 revoke-security-group-egress --group-id <DEFAULT_SG_ID> --protocol all --cidr 0.0.0.0/0"
        ),
        terraform_snippet=(
            'resource "aws_default_security_group" "default" {\n'
            "  vpc_id = aws_vpc.main.id\n'  # Empty ingress/egress blocks ensure all traffic is denied\n"
            "}"
        ),
        verification_command=(
            "aws ec2 describe-security-groups \\\n"
            '  --filters "Name=group-name,Values=default" \\\n'
            "  --query 'SecurityGroups[*].[GroupId, IpPermissions, IpPermissionsEgress]'"
        ),
    ),

    "config_recorder_enabled": RemediationGuide(
        control_id="config_recorder_enabled",
        title="Enable AWS Config Configuration Recorder",
        threat_rationale="Without AWS Config, cloud asset drift, unapproved configuration changes, and compliance state cannot be tracked historically.",
        estimated_time_minutes=6,
        console_steps=[
            "Open the AWS Config console at https://console.aws.amazon.com/config/.",
            "Choose 'Get started' or 'Settings'.",
            "Under 'Recording strategy', choose 'Record all current and future resource types'.",
            "Under 'Data governance', select your Amazon S3 bucket for configuration snapshots.",
            "Choose 'Save'.",
        ],
        aws_cli_command=(
            "aws configservice start-configuration-recorder \\\n"
            "  --configuration-recorder-name default"
        ),
        terraform_snippet=(
            'resource "aws_config_configuration_recorder" "main" {\n'
            '  name     = "default"\n'
            "  role_arn = aws_iam_role.config_role.arn\n"
            "  recording_group {\n"
            "    all_supported                 = true\n"
            "    include_global_resource_types = true\n"
            "  }\n"
            "}\n"
            'resource "aws_config_configuration_recorder_status" "main" {\n'
            "  name       = aws_config_configuration_recorder.main.name\n"
            "  is_enabled = true\n"
            "}"
        ),
        verification_command="aws configservice describe-configuration-recorder-status",
    ),

    "securityhub_enabled": RemediationGuide(
        control_id="securityhub_enabled",
        title="Enable AWS Security Hub",
        threat_rationale="Security Hub aggregates posture alerts and security findings across GuardDuty, Inspector, and Config in a unified console.",
        estimated_time_minutes=4,
        console_steps=[
            "Open the AWS Security Hub console at https://console.aws.amazon.com/securityhub/.",
            "Choose 'Go to Security Hub'.",
            "Enable 'AWS Foundational Security Best Practices' and 'CIS AWS Foundations Benchmark'.",
            "Choose 'Enable Security Hub'.",
        ],
        aws_cli_command=(
            "aws securityhub enable-security-hub \\\n"
            "  --enable-default-standards"
        ),
        terraform_snippet=(
            'resource "aws_securityhub_account" "main" {\n'
            "  enable_default_standards = true\n"
            "}"
        ),
        verification_command="aws securityhub describe-hub",
    ),

    "guardduty_enabled": RemediationGuide(
        control_id="guardduty_enabled",
        title="Enable Amazon GuardDuty Threat Detection",
        threat_rationale="GuardDuty detects active credential compromise, cryptocurrency mining, and anomalous API behavior using machine learning.",
        estimated_time_minutes=3,
        console_steps=[
            "Open the GuardDuty console at https://console.aws.amazon.com/guardduty/.",
            "Choose 'Get Started'.",
            "Choose 'Enable GuardDuty'.",
        ],
        aws_cli_command="aws guardduty create-detector --enable",
        terraform_snippet=(
            'resource "aws_guardduty_detector" "primary" {\n'
            "  enable = true\n"
            "}"
        ),
        verification_command=(
            "aws guardduty list-detectors --query 'DetectorIds[0]'"
        ),
    ),

    "vpc_flow_logs_enabled": RemediationGuide(
        control_id="vpc_flow_logs_enabled",
        title="Enable VPC Flow Logs for All VPCs",
        threat_rationale="Without flow logs, security teams cannot reconstruct network ingress/egress connections during a breach investigation.",
        estimated_time_minutes=5,
        console_steps=[
            "Open the Amazon VPC console at https://console.aws.amazon.com/vpc/.",
            "In the navigation pane, choose 'Your VPCs'.",
            "Select your VPC, choose the 'Flow logs' tab, and click 'Create flow log'.",
            "Set Filter to 'ALL'.",
            "Set Destination to 'Send to CloudWatch Logs' or 'Send to an S3 bucket'.",
            "Choose 'Create flow log'.",
        ],
        aws_cli_command=(
            "aws ec2 create-flow-logs \\\n"
            "  --resource-type VPC \\\n"
            "  --resource-ids <VPC_ID> \\\n"
            "  --traffic-type ALL \\\n"
            "  --log-destination-type s3 \\\n"
            "  --log-destination <S3_BUCKET_ARN>"
        ),
        terraform_snippet=(
            'resource "aws_flow_log" "vpc_traffic" {\n'
            "  log_destination      = aws_s3_bucket.flow_logs.arn\n"
            '  log_destination_type = "s3"\n'
            '  traffic_type         = "ALL"\n'
            "  vpc_id               = aws_vpc.main.id\n"
            "}"
        ),
        verification_command=(
            "aws ec2 describe-flow-logs --query 'FlowLogs[*].[FlowLogId, TrafficType, FlowLogStatus]'"
        ),
    ),

    "kms_key_rotation_rate": RemediationGuide(
        control_id="kms_key_rotation_rate",
        title="Enable Automatic Annual Rotation for AWS KMS Customer-Managed Keys",
        threat_rationale="Cryptographic key rotation limits the volume of data ciphered under a single key version, reducing blast radius if a key is compromised.",
        estimated_time_minutes=2,
        console_steps=[
            "Open the AWS KMS console at https://console.aws.amazon.com/kms/.",
            "In the navigation pane, choose 'Customer managed keys'.",
            "Choose the key name.",
            "Choose the 'Key rotation' tab.",
            "Select 'Automatically rotate this KMS key every year'.",
            "Choose 'Save'.",
        ],
        aws_cli_command=(
            "aws kms enable-key-rotation \\\n"
            "  --key-id <KMS_KEY_ID>"
        ),
        terraform_snippet=(
            'resource "aws_kms_key" "data_key" {\n'
            '  description             = "Compliance data encryption key"\n'
            "  enable_key_rotation     = true\n"
            "  deletion_window_in_days = 30\n"
            "}"
        ),
        verification_command=(
            "aws kms get-key-rotation-status --key-id <KMS_KEY_ID>"
        ),
    ),

    "backup_configured": RemediationGuide(
        control_id="backup_configured",
        title="Configure Centralized AWS Backup Plan for Critical Datastores",
        threat_rationale="Ransomware or operational errors can cause permanent business data destruction without immutable, centralized recovery points.",
        estimated_time_minutes=8,
        console_steps=[
            "Open AWS Backup console at https://console.aws.amazon.com/backup/.",
            "Choose 'Create backup plan' and select 'Build a new plan'.",
            "Name the plan 'Daily-Compliance-Backup'.",
            "Set Backup frequency to 'Daily' and retention period to '35 days' (or per your policy).",
            "Under 'Assign resources', assign tags corresponding to production databases and EBS volumes.",
            "Choose 'Assign resources'.",
        ],
        aws_cli_command=(
            "aws backup create-backup-plan \\\n"
            '  --backup-plan \'{"BackupPlanName":"CompliancePlan","Rules":[{"RuleName":"DailyRule","TargetBackupVaultName":"Default","ScheduleExpression":"cron(0 12 * * ? *)","StartWindowMinutes":60,"CompletionWindowMinutes":120,"Lifecycle":{"DeleteAfterDays":35}}]}\''
        ),
        terraform_snippet=(
            'resource "aws_backup_plan" "compliance" {\n'
            '  name = "production-compliance-plan"\n'
            "  rule {\n"
            '    rule_name         = "daily_backup"\n'
            '    target_vault_name = "default"\n'
            '    schedule          = "cron(0 12 * * ? *)"\n'
            "    lifecycle {\n"
            "      delete_after = 35\n"
            "    }\n"
            "  }\n"
            "}"
        ),
        verification_command="aws backup list-backup-plans --query 'BackupPlansList[*].[BackupPlanName, BackupPlanId]'",
    ),

    "iam_stale_access_keys": RemediationGuide(
        control_id="iam_stale_access_keys",
        title="Deactivate and Rotate IAM Access Keys Older Than 90 Days",
        threat_rationale="Static IAM keys forgotten on developer workstations or CI/CD pipelines represent the top target for cloud attackers.",
        estimated_time_minutes=10,
        console_steps=[
            "Open the IAM console at https://console.aws.amazon.com/iam/.",
            "Choose 'Users' and sort by 'Access key age'.",
            "For keys older than 90 days, select the user and choose 'Security credentials'.",
            "Create a new access key, deploy it to your application, and verify traffic.",
            "Change the old key status to 'Inactive'.",
            "After 7 days of monitoring, 'Delete' the inactive key.",
        ],
        aws_cli_command=(
            "# Deactivate key:\n"
            "aws iam update-access-key --user-name <USER_NAME> --access-key-id <KEY_ID> --status Inactive\n"
            "# After verification, delete:\n"
            "aws iam delete-access-key --user-name <USER_NAME> --access-key-id <KEY_ID>"
        ),
        terraform_snippet=(
            "# Prefer IAM Roles for service authentication over static keys.\n"
            "# If static keys are strictly required, automate rotation using AWS Secrets Manager."
        ),
        verification_command=(
            "aws iam list-access-keys --user-name <USER_NAME>"
        ),
    ),
}


# ═════════════════════════════════════════════════════════════════════════════
# Control ID Mapping Crosswalk (SOC 2, ISO 27001, CIS AWS, etc.)
# ═════════════════════════════════════════════════════════════════════════════

CONTROL_TO_PRIMARY_SIGNAL: dict[str, str] = {
    # SOC 2 Common Criteria
    "CC6.1": "iam_root_mfa_enabled",
    "CC6.2": "iam_mfa_enforcement_rate",
    "CC6.3": "iam_stale_access_keys",
    "CC6.6": "open_security_groups",
    "CC6.7": "ebs_default_encryption",
    "CC6.8": "guardduty_enabled",
    "CC7.1": "config_recorder_enabled",
    "CC7.2": "cloudtrail_log_validation",
    "CC7.3": "cloudtrail_multiregion",
    "CC7.4": "securityhub_enabled",
    "A1.2":  "backup_configured",

    # CIS AWS Foundations Benchmark
    "cis_aws.1.4": "iam_root_mfa_enabled",
    "cis_aws.1.5": "iam_mfa_enforcement_rate",
    "cis_aws.1.14": "iam_stale_access_keys",
    "cis_aws.2.1.1": "s3_public_access_blocked",
    "cis_aws.2.2.1": "ebs_default_encryption",
    "cis_aws.2.3.1": "rds_encryption_rate",
    "cis_aws.3.1": "cloudtrail_multiregion",
    "cis_aws.3.2": "cloudtrail_log_validation",
    "cis_aws.3.7": "cloudtrail_encrypted",
    "cis_aws.3.9": "config_recorder_enabled",
    "cis_aws.4.1": "open_security_groups",
    "cis_aws.4.3": "default_sg_restricted",
    "cis_aws.4.4": "vpc_flow_logs_enabled",
}


def get_remediation_guide(
    control_id: str,
    signals: Iterable[str] | None = None,
    control_name: str = "",
    guidance: str = "",
) -> RemediationGuide:
    """
    Resolve or synthesize an actionable RemediationGuide for any compliance control.

    Lookup hierarchy:
    1. Direct match on control_id in SIGNAL_REMEDIATION_CATALOG.
    2. Primary signal mapped via CONTROL_TO_PRIMARY_SIGNAL.
    3. First signal match from the control's referenced signals list.
    4. Deterministic structured fallback populated with control guidance.
    """
    # 1. Direct match
    if control_id in SIGNAL_REMEDIATION_CATALOG:
        return SIGNAL_REMEDIATION_CATALOG[control_id]

    # 2. Control ID to primary signal map
    primary_sig = CONTROL_TO_PRIMARY_SIGNAL.get(control_id)
    if primary_sig and primary_sig in SIGNAL_REMEDIATION_CATALOG:
        base = SIGNAL_REMEDIATION_CATALOG[primary_sig]
        return base.model_copy(update={"control_id": control_id})

    # 3. Referenced signals in control definition
    if signals:
        for sig in signals:
            if sig in SIGNAL_REMEDIATION_CATALOG:
                base = SIGNAL_REMEDIATION_CATALOG[sig]
                return base.model_copy(update={"control_id": control_id})

    # 4. Fallback generator using control metadata
    title = f"Remediate {control_id}: {control_name}" if control_name else f"Remediate Control {control_id}"
    rationale = guidance or "Ensure this control satisfies the regulatory standard and minimizes cloud exposure."
    
    return RemediationGuide(
        control_id=control_id,
        title=title,
        threat_rationale=rationale,
        estimated_time_minutes=10,
        console_steps=[
            f"Review the control requirement: {control_name or control_id}.",
            "Inspect the underlying cloud assets flagged in the evidence gaps.",
            f"Apply the remediation policy: {guidance or 'Configure the resource to adhere to baseline standards.'}",
            "Verify that no unexpected dependent services are disrupted.",
        ],
        aws_cli_command=f"# Review affected resources for {control_id}:\naws resourcegroupstaggingapi get-resources",
        terraform_snippet=f"# Review and enforce compliance policy in Terraform for {control_id}:\n# Refer to organization baseline module.",
        verification_command="# Re-run LogRaven compliance scan to confirm gap resolution.",
    )
