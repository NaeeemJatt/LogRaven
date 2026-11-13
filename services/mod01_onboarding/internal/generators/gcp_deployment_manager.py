"""GCP Deployment Manager / Resource Manager YAML template generator for LogRaven Onboarding."""

import yaml


def generate_gcp_deployment_manager(
    tenant_id: str,
    project_id: str,
    service_account_name: str = "lograven-cspm-reader",
) -> str:
    """Generate GCP Deployment Manager YAML configuration."""
    config = {
        "resources": [
            {
                "name": service_account_name,
                "type": "iam.v1.serviceAccount",
                "properties": {
                    "accountId": service_account_name,
                    "displayName": f"LogRaven CSPM Reader for Tenant {tenant_id}",
                },
            },
            {
                "name": f"bind-viewer-{tenant_id[:8]}",
                "type": "gcp-types/cloudresourcemanager-v1:virtual.projects.iamMemberBinding",
                "properties": {
                    "resource": project_id,
                    "role": "roles/viewer",
                    "member": f"serviceAccount:{service_account_name}@{project_id}.iam.gserviceaccount.com",
                },
            },
            {
                "name": f"bind-security-reviewer-{tenant_id[:8]}",
                "type": "gcp-types/cloudresourcemanager-v1:virtual.projects.iamMemberBinding",
                "properties": {
                    "resource": project_id,
                    "role": "roles/iam.securityReviewer",
                    "member": f"serviceAccount:{service_account_name}@{project_id}.iam.gserviceaccount.com",
                },
            },
        ],
        "outputs": [
            {
                "name": "serviceAccountEmail",
                "value": f"{service_account_name}@{project_id}.iam.gserviceaccount.com",
            }
        ],
    }
    return yaml.dump(config, sort_keys=False)

