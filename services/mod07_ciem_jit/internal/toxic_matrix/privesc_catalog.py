"""Catalog of 21 Known Cloud Privilege Escalation Vectors (FR-MOD7-02, TC-MOD7-002).

Derived from Rhino Security Labs & SpecterOps cloud research covering AWS, Azure, and GCP.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class PrivEscVector:
    id: str
    cloud_provider: str
    title: str
    severity: str  # CRITICAL | HIGH
    required_actions: List[str]
    description: str
    mitigation: str


PRIVESC_CATALOG: List[PrivEscVector] = [
    PrivEscVector(
        id="AWS-PRIVESC-001",
        cloud_provider="aws",
        title="Create New IAM Policy Version",
        severity="CRITICAL",
        required_actions=["iam:CreatePolicyVersion"],
        description="Principal can create a new version of an attached IAM policy with AdministratorAccess.",
        mitigation="Restrict iam:CreatePolicyVersion or enforce permission boundary.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-002",
        cloud_provider="aws",
        title="Launch EC2 Instance with Existing Administrative Role",
        severity="CRITICAL",
        required_actions=["iam:PassRole", "ec2:RunInstances"],
        description="Principal can launch an EC2 instance with an administrative IAM role attached, then retrieve instance credentials via IMDS.",
        mitigation="Restrict iam:PassRole to specific non-admin role ARNs.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-003",
        cloud_provider="aws",
        title="Set Default Policy Version",
        severity="HIGH",
        required_actions=["iam:SetDefaultPolicyVersion"],
        description="Principal can switch an existing policy to a previously created permissive version.",
        mitigation="Prune old IAM policy versions and restrict iam:SetDefaultPolicyVersion.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-004",
        cloud_provider="aws",
        title="Attach Policy to Principal",
        severity="CRITICAL",
        required_actions=["iam:AttachUserPolicy"],
        description="Principal can attach AdministratorAccess policy directly to themselves.",
        mitigation="Enforce permission boundaries and restrict iam:AttachUserPolicy.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-005",
        cloud_provider="aws",
        title="Attach Role Policy",
        severity="CRITICAL",
        required_actions=["iam:AttachRolePolicy"],
        description="Principal can attach policies to roles they are authorized to assume.",
        mitigation="Restrict iam:AttachRolePolicy to specific non-admin policies.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-006",
        cloud_provider="aws",
        title="Put Inline User Policy",
        severity="CRITICAL",
        required_actions=["iam:PutUserPolicy"],
        description="Principal can write an inline AdministratorAccess policy directly to their user.",
        mitigation="Deny iam:PutUserPolicy across the organization.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-007",
        cloud_provider="aws",
        title="Put Inline Role Policy",
        severity="CRITICAL",
        required_actions=["iam:PutRolePolicy"],
        description="Principal can inject arbitrary permissions into assumable IAM roles.",
        mitigation="Deny iam:PutRolePolicy without secondary approval.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-008",
        cloud_provider="aws",
        title="Create Access Key for Another User",
        severity="CRITICAL",
        required_actions=["iam:CreateAccessKey"],
        description="Principal can generate new access keys for high-privilege administrators.",
        mitigation="Restrict iam:CreateAccessKey to self only (Condition: aws:username).",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-009",
        cloud_provider="aws",
        title="Create Lambda Function with Admin Role",
        severity="CRITICAL",
        required_actions=["iam:PassRole", "lambda:CreateFunction"],
        description="Principal can deploy arbitrary code into AWS Lambda executing under an administrative role.",
        mitigation="Restrict iam:PassRole for Lambda execution roles.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-010",
        cloud_provider="aws",
        title="Update Lambda Function Code",
        severity="HIGH",
        required_actions=["lambda:UpdateFunctionCode"],
        description="Principal can overwrite code in an existing Lambda function possessing elevated privileges.",
        mitigation="Protect critical Lambda functions with strict resource policies.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-011",
        cloud_provider="aws",
        title="Create Glue Dev Endpoint",
        severity="HIGH",
        required_actions=["iam:PassRole", "glue:CreateDevEndpoint"],
        description="Principal can launch a Glue development endpoint with an administrative IAM role.",
        mitigation="Restrict glue:CreateDevEndpoint permissions.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-012",
        cloud_provider="aws",
        title="Create CloudFormation Stack with Admin Role",
        severity="CRITICAL",
        required_actions=["iam:PassRole", "cloudformation:CreateStack"],
        description="Principal can deploy infrastructure through CloudFormation using an administrative service role.",
        mitigation="Restrict cloudformation:CreateStack service role delegation.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-013",
        cloud_provider="aws",
        title="Create CodeBuild Project with Admin Role",
        severity="HIGH",
        required_actions=["iam:PassRole", "codebuild:CreateProject"],
        description="Principal can run arbitrary build scripts inside AWS CodeBuild with administrative credentials.",
        mitigation="Scope CodeBuild execution roles.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-014",
        cloud_provider="aws",
        title="Update AssumeRolePolicy Document",
        severity="CRITICAL",
        required_actions=["iam:UpdateAssumeRolePolicy"],
        description="Principal can alter the trust relationship of an administrative role to assume it.",
        mitigation="Deny iam:UpdateAssumeRolePolicy.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-015",
        cloud_provider="aws",
        title="Create Login Profile / Password Reset",
        severity="CRITICAL",
        required_actions=["iam:CreateLoginProfile"],
        description="Principal can enable console password login for existing high-privilege users.",
        mitigation="Restrict iam:CreateLoginProfile.",
    ),
    # Azure RBAC Vectors
    PrivEscVector(
        id="AZURE-PRIVESC-001",
        cloud_provider="azure",
        title="Write Role Assignment",
        severity="CRITICAL",
        required_actions=["Microsoft.Authorization/roleAssignments/write"],
        description="Principal can assign Owner or Contributor roles to themselves.",
        mitigation="Restrict roleAssignments/write to Global Admins.",
    ),
    PrivEscVector(
        id="AZURE-PRIVESC-002",
        cloud_provider="azure",
        title="Execute Automation Runbook as Admin",
        severity="HIGH",
        required_actions=["Microsoft.Automation/automationAccounts/runbooks/write"],
        description="Principal can inject code into Azure Automation runbooks with Managed Identity.",
        mitigation="Protect automation runbooks.",
    ),
    # GCP IAM Vectors
    PrivEscVector(
        id="GCP-PRIVESC-001",
        cloud_provider="gcp",
        title="Set Project IAM Policy",
        severity="CRITICAL",
        required_actions=["resourcemanager.projects.setIamPolicy"],
        description="Principal can grant roles/owner to any identity at project level.",
        mitigation="Restrict resourcemanager.projects.setIamPolicy.",
    ),
    PrivEscVector(
        id="GCP-PRIVESC-002",
        cloud_provider="gcp",
        title="ActAs Service Account Token Creator",
        severity="CRITICAL",
        required_actions=["iam.serviceAccounts.actAs", "iam.serviceAccounts.getAccessToken"],
        description="Principal can impersonate administrative Google Cloud Service Accounts.",
        mitigation="Restrict iam.serviceAccountTokenCreator.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-016",
        cloud_provider="aws",
        title="Add User to Administrative Group",
        severity="CRITICAL",
        required_actions=["iam:AddUserToGroup"],
        description="Principal can add themselves to the Administrators group.",
        mitigation="Restrict iam:AddUserToGroup.",
    ),
    PrivEscVector(
        id="AWS-PRIVESC-017",
        cloud_provider="aws",
        title="Create Access Policy with Admin Wildcard",
        severity="CRITICAL",
        required_actions=["iam:CreatePolicy"],
        description="Principal can craft customer managed policies with full administrative capabilities.",
        mitigation="Enforce permission boundaries on created policies.",
    ),
]
