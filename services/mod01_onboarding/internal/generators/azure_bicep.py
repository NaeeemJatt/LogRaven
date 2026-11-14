"""Azure Bicep Template Synthesizer for LogRaven Enterprise Onboarding."""

def generate_azure_bicep(
    tenant_id: str,
    principal_id: str = "00000000-0000-0000-0000-000000000000",
) -> str:
    """Generate Azure Bicep template creating reader role assignments for LogRaven."""
    return f"""// LogRaven Enterprise Azure Onboarding Bicep Template
// Tenant ID: {tenant_id}

targetScope = 'subscription'

@description('Object ID of the LogRaven multi-tenant Enterprise Service Principal')
param logRavenPrincipalId string = '{principal_id}'

// Built-in Reader role ID: acdd72a7-3385-48ef-bd42-f606fba81ae7
resource readerAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {{
  name: guid(subscription().id, logRavenPrincipalId, 'Reader')
  properties: {{
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'acdd72a7-3385-48ef-bd42-f606fba81ae7')
    principalId: logRavenPrincipalId
    principalType: 'ServicePrincipal'
  }}
}}

// Built-in Security Reader role ID: 39bc4728-0916-4830-b766-d541dd42b4e6
resource securityReaderAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {{
  name: guid(subscription().id, logRavenPrincipalId, 'SecurityReader')
  properties: {{
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '39bc4728-0916-4830-b766-d541dd42b4e6')
    principalId: logRavenPrincipalId
    principalType: 'ServicePrincipal'
  }}
}}

output subscriptionId string = subscription().subscriptionId
output principalAssigned string = logRavenPrincipalId
"""

