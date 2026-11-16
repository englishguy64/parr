// Backend API (App Service) in snet-api. It is reached only through API Management and calls Foundry
// through the private endpoint, using its own managed identity.
// Deploy create_network.bicep and create_foundry.bicep first.

@description('Backend API web app name. Must be globally unique (becomes <name>.azurewebsites.net).')
param backendName string

@description('Name of the App Service plan. The Backend API and the website (create_webapp.bicep) share it, so this template creates it.')
param appServicePlanName string

@description('Storage account for the sample receipt (3 to 24 lowercase letters and numbers, globally unique).')
@minLength(3)
@maxLength(24)
param storageAccountName string

@description('App Service plan SKU. Pick one that has capacity in the region, for example B1, S1 or P0v3.')
param appServiceSku string = 'P0v3'

@description('Virtual network created by create_network.bicep.')
param vnetName string = 'vnet-ai'

@description('Existing Foundry resource (Azure AI Services account) name.')
param foundryName string

@description('Existing Foundry project name.')
param projectName string

@description('Chat model deployment the agents use.')
param modelDeploymentName string = 'gpt-4.1-mini'

param location string = 'germanywestcentral'

// Built-in role: Azure AI User (data-plane access to run agents).
var azureAiUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName
}

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

// Storage for the sample receipt (the PNG itself is uploaded by create_samplereceipt.bicep into a "samples" container).
// Access is by Entra ID only: no account keys, no SAS links and no anonymous reads, so a link on its own opens nothing.
// The Foundry project identity (which the Hosted Agents run as) reads the file, so Order Lookup downloads it itself and
// hands the bytes to Document Intelligence. The Backend API only adds the file's address to the message. The storage
// account is not in the VNet.
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled'
  }
}

// Where create_samplereceipt.bicep puts the sample receipt. The Backend API adds this address to a message about a receipt.
var sampleReceiptUrl = '${storage.properties.primaryEndpoints.blob}samples/sample-receipt.png'

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: appServicePlanName
  location: location
  sku: { name: appServiceSku }
  kind: 'linux'
  properties: { reserved: true }
}

resource backend 'Microsoft.Web/sites@2024-04-01' = {
  name: backendName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    virtualNetworkSubnetId: '${vnet.id}/subnets/snet-api'
    vnetRouteAllEnabled: true // Foundry's name must resolve to the private endpoint through the VNet
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      // Inbound: only API Management (snet-apim, through its Microsoft.Web service endpoint) may call this app.
      ipSecurityRestrictionsDefaultAction: 'Deny'
      ipSecurityRestrictions: [
        {
          name: 'allow-apim-subnet'
          priority: 100
          action: 'Allow'
          vnetSubnetResourceId: '${vnet.id}/subnets/snet-apim'
        }
      ]
      appSettings: [
        { name: 'FOUNDRY_PROJECT_ENDPOINT', value: 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}' }
        { name: 'FOUNDRY_MODEL_DEPLOYMENT', value: modelDeploymentName }
        // Which Foundry agent answers each choice on the website (names match create_foundrypromptagents and create_foundryhostedagents).
        { name: 'SAMPLE_RECEIPT_URL', value: sampleReceiptUrl }
        { name: 'AGENT_SUPPORT', value: '${foundryName}-agentone' }
        { name: 'AGENT_RESEARCH', value: '${foundryName}-agenttwo' }
        { name: 'AGENT_ORCHESTRATOR', value: '${foundryName}-orchestrator' }
        { name: 'AGENT_ORDER_LOOKUP', value: '${foundryName}-order-lookup' }
      ]
    }
  }
}

// The Backend API's managed identity runs the agents.
resource backendFoundryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, backend.id, azureAiUserRoleId)
  scope: foundry
  properties: {
    principalId: backend.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAiUserRoleId)
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: foundry
  name: projectName
}

// The Foundry project identity (what the Hosted Agents run as) can read the sample receipt, so Order Lookup can download it.
var blobDataReaderRoleId = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
resource agentsReadSamples'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, project.id, blobDataReaderRoleId)
  scope: storage
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobDataReaderRoleId)
  }
}

output storageAccountName string = storage.name
output appServicePlanName string = plan.name
output backendUrl string = 'https://${backend.properties.defaultHostName}'
