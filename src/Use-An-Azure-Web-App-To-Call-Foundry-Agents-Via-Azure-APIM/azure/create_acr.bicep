// Azure Container Registry for the Hosted Agent container images (orchestrator, order lookup and policy check).
// Basic tier: cheapest, with a public endpoint (no private endpoint). Access is Entra ID only:
// the admin user and anonymous pull are off, and the Foundry project identity pulls images with the AcrPull role.
// Deploy create_foundry.bicep first (the project identity must exist).

@description('Registry name. Globally unique, 5-50 lowercase letters and numbers.')
param acrName string

@description('Existing Foundry resource name.')
param foundryName string

@description('Existing Foundry project name.')
param projectName string

@allowed(['Basic', 'Standard'])
param sku string = 'Basic'

param location string = 'germanywestcentral'

// Built-in role: AcrPull.
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: foundry
  name: projectName
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: sku }
  properties: {
    adminUserEnabled: false // no shared username/password: Entra ID only
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

// The Foundry project identity pulls the Hosted Agent images.
resource pull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, project.id, acrPullRoleId)
  scope: acr
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

output loginServer string = acr.properties.loginServer
