// Microsoft Foundry resource + project + chat model deployment, reached through a private endpoint in snet-pe.
// Deploy create_network.bicep first. Agents are created by create_foundrypromptagents.bicep.
//
// Creating the agents calls the Foundry data plane from outside the VNet, so deploy with
// publicNetworkAccess = 'Enabled' (the default), create the agents, then redeploy with 'Disabled'.

@description('Foundry resource (Azure AI Services account) name. Also used as the custom subdomain.')
param foundryName string

@description('Foundry project name.')
param projectName string

@description('Virtual network created by create_network.bicep.')
param vnetName string = 'vnet-ai'

@description('Set to Disabled once the agents exist, so Foundry is reachable only through the private endpoint.')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

param location string = 'germanywestcentral'

@description('Chat model sold directly by Azure (a moderate-cost chatbot model).')
param modelName string = 'gpt-4.1-mini'
param modelVersion string = '2025-04-14'
param modelDeploymentName string = 'gpt-4.1-mini'
param modelCapacity int = 50

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName
}

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: foundryName
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    customSubDomainName: toLower(foundryName)
    disableLocalAuth: true // Entra ID auth only
    publicNetworkAccess: publicNetworkAccess
    networkAcls: { defaultAction: publicNetworkAccess == 'Enabled' ? 'Allow' : 'Deny' }
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: foundry
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: projectName
    description: '${projectName} Foundry project'
  }
}

resource model 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: foundry
  name: modelDeploymentName
  sku: { name: 'GlobalStandard', capacity: modelCapacity }
  properties: {
    model: { format: 'OpenAI', name: modelName, version: modelVersion }
  }
  dependsOn: [project]
}

// ---------- private endpoint in snet-pe ----------
resource pe 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: '${foundryName}-pe'
  location: location
  properties: {
    subnet: { id: '${vnet.id}/subnets/snet-pe' }
    privateLinkServiceConnections: [
      {
        name: 'foundry'
        properties: { privateLinkServiceId: foundry.id, groupIds: ['account'] }
      }
    ]
  }
  dependsOn: [model]
}

resource zoneAi 'Microsoft.Network/privateDnsZones@2024-06-01' existing = { name: 'privatelink.services.ai.azure.com' }
resource zoneCog 'Microsoft.Network/privateDnsZones@2024-06-01' existing = { name: 'privatelink.cognitiveservices.azure.com' }
resource zoneOai 'Microsoft.Network/privateDnsZones@2024-06-01' existing = { name: 'privatelink.openai.azure.com' }

resource peDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: pe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      { name: 'ai', properties: { privateDnsZoneId: zoneAi.id } }
      { name: 'cognitive', properties: { privateDnsZoneId: zoneCog.id } }
      { name: 'openai', properties: { privateDnsZoneId: zoneOai.id } }
    ]
  }
}

output projectEndpoint string = 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
output modelDeployment string = model.name
