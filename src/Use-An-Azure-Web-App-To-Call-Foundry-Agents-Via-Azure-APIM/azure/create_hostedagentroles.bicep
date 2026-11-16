// Roles the Hosted Agents need to read receipts. Run it after create_foundryhostedagents.bicep (the agents must exist).
//
//   - Cognitive Services User on the Foundry resource: lets Order Lookup call Document Intelligence.
//     Given to the Foundry project identity (what the agents normally run as) and to Order Lookup's own agent identity.
//   - Storage Blob Data Reader on the storage account: lets Order Lookup download the sample receipt with its own identity.
//     (The project identity already has it from create_backendapi.bicep.)
//
// Every new version of a Hosted Agent gets a NEW identity, so the agent's roles must be granted again after you create
// a new version. 15_create-hostedagentroles.ps1 looks up the current identity and runs this template.

@description('Existing Foundry resource (Azure AI Services account) name.')
param foundryName string

@description('Existing Foundry project name.')
param projectName string

@description('Storage account that holds the sample receipt (create_backendapi.bicep).')
param storageAccountName string

@description('Object id of the Order Lookup agent version that is running now (its instance identity).')
param orderLookupPrincipalId string

// Built-in roles.
var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var blobDataReaderRoleId = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: foundry
  name: projectName
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// Document Intelligence: the project identity.
resource projectDocIntelligence 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, project.id, cognitiveServicesUserRoleId)
  scope: foundry
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
  }
}

// Document Intelligence: Order Lookup's own identity.
resource orderLookupDocIntelligence 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, orderLookupPrincipalId, cognitiveServicesUserRoleId)
  scope: foundry
  properties: {
    principalId: orderLookupPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
  }
}

// Reading the receipt blob: Order Lookup's own identity.
resource orderLookupBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, orderLookupPrincipalId, blobDataReaderRoleId)
  scope: storage
  properties: {
    principalId: orderLookupPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobDataReaderRoleId)
  }
}
