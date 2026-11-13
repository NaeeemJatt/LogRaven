"""Terraform HCL Template Synthesis Engine for AWS, Azure, and GCP Onboarding."""

from typing import Optional


def generate_aws_terraform(
    tenant_id: str,
    external_id: str,
    lograven_account_id: str = "112233445566",
    role_name: str = "LogRavenCSPMReader",
    event_bus_region: str = "us-east-1",
) -> str:
    """Generate production-grade Terraform HCL for AWS CSPM cross-account trust."""
    event_bus_arn = f"arn:aws:events:{event_bus_region}:{lograven_account_id}:event-bus/lr-ingest-{tenant_id}"

    return f"""# ── LogRaven AWS Cross-Account Trust & Telemetry ─────────────
# Automatically generated for Tenant: {tenant_id}

terraform {{
  required_version = ">= 1.5.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }}
  }}
}}

variable "lograven_external_id" {{
  type        = string
  default     = "{external_id}"
  description = "Cryptographic ExternalId assigned by LogRaven Trust Broker"
  sensitive   = true
}}

variable "lograven_account_id" {{
  type        = string
  default     = "{lograven_account_id}"
  description = "LogRaven Enterprise Cloud Account ID"
}}

data "aws_iam_policy_document" "lograven_trust" {{
  statement {{
    effect = "Allow"
    principals {{
      type        = "AWS"
      identifiers = ["arn:aws:iam::${{var.lograven_account_id}}:root"]
    }}
    actions = ["sts:AssumeRole"]
    condition {{
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [var.lograven_external_id]
    }}
  }}
}}

resource "aws_iam_role" "lograven_reader" {{
  name               = "{role_name}"
  assume_role_policy = data.aws_iam_policy_document.lograven_trust.json
  description        = "Read-only cross-account role for LogRaven CSPM and Threat Engine"

  tags = {{
    ManagedBy = "LogRaven"
    TenantId  = "{tenant_id}"
  }}
}}

resource "aws_iam_role_policy_attachment" "security_audit" {{
  role       = aws_iam_role.lograven_reader.name
  policy_arn = "arn:aws:iam::aws:policy/SecurityAudit"
}}

resource "aws_iam_policy" "lograven_supplemental" {{
  name        = "LogRavenSupplementalPolicy-{tenant_id[:8]}"
  description = "Scoped read and EventBridge telemetry permissions for LogRaven"

  policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Sid      = "AllowTelemetryForwarding"
        Effect   = "Allow"
        Action   = ["events:PutEvents"]
        Resource = "{event_bus_arn}"
      }},
      {{
        Sid    = "AllowSupplementalCSPMReads"
        Effect = "Allow"
        Action = [
          "s3:GetEncryptionConfiguration",
          "s3:GetBucketPublicAccessBlock",
          "s3:GetBucketPolicyStatus",
          "kms:GetKeyRotationStatus",
          "iam:SimulatePrincipalPolicy",
          "access-analyzer:ListFindings"
        ]
        Resource = "*"
      }}
    ]
  }})
}}

resource "aws_iam_role_policy_attachment" "supplemental" {{
  role       = aws_iam_role.lograven_reader.name
  policy_arn = aws_iam_policy.lograven_supplemental.arn
}}

output "lograven_role_arn" {{
  value       = aws_iam_role.lograven_reader.arn
  description = "Copy and paste this Role ARN into LogRaven onboarding"
}}
"""


def generate_azure_terraform(
    tenant_id: str,
    subscription_id: str = "00000000-0000-0000-0000-000000000000",
    client_id: Optional[str] = None,
) -> str:
    """Generate Terraform HCL for Azure Entra ID / Subscription read access."""
    c_id = client_id or "00000000-0000-0000-0000-000000000000"
    return f"""# ── LogRaven Azure Reader Role Assignment ────────────────────
# Generated for Tenant: {tenant_id}

terraform {{
  required_version = ">= 1.5.0"
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = ">= 3.70.0"
    }}
  }}
}}

provider "azurerm" {{
  features {{}}
  subscription_id = "{subscription_id}"
}}

variable "lograven_sp_client_id" {{
  type        = string
  default     = "{c_id}"
  description = "Application / Service Principal Client ID"
}}

resource "azurerm_role_assignment" "reader" {{
  scope                = "/subscriptions/{subscription_id}"
  role_definition_name = "Reader"
  principal_id         = var.lograven_sp_client_id
}}

resource "azurerm_role_assignment" "security_reader" {{
  scope                = "/subscriptions/{subscription_id}"
  role_definition_name = "Security Reader"
  principal_id         = var.lograven_sp_client_id
}}

output "subscription_id" {{
  value = "{subscription_id}"
}}
"""


def generate_gcp_terraform(
    tenant_id: str,
    project_id: str,
    pool_id: str = "lograven-wif-pool",
) -> str:
    """Generate Terraform HCL for GCP Workload Identity Federation & Service Account."""
    return f"""# ── LogRaven GCP Workload Identity Federation ────────────────
# Generated for Tenant: {tenant_id}

terraform {{
  required_version = ">= 1.5.0"
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = ">= 5.0"
    }}
  }}
}}

provider "google" {{
  project = "{project_id}"
}}

resource "google_service_account" "lograven_reader" {{
  account_id   = "lograven-cspm-reader"
  display_name = "LogRaven CSPM & Telemetry Service Account"
}}

resource "google_project_iam_member" "viewer" {{
  project = "{project_id}"
  role    = "roles/viewer"
  member  = "serviceAccount:${{google_service_account.lograven_reader.email}}"
}}

resource "google_project_iam_member" "security_reviewer" {{
  project = "{project_id}"
  role    = "roles/iam.securityReviewer"
  member  = "serviceAccount:${{google_service_account.lograven_reader.email}}"
}}

output "service_account_email" {{
  value = google_service_account.lograven_reader.email
}}
"""

