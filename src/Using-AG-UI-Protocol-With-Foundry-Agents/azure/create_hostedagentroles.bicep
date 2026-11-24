// Lets the deployed hosted agents call the chat model in the Foundry project.
//
// Each hosted agent runs as its own identity (shown as instance_identity.principal_id on the agent). The agent code signs in
// with DefaultAzureCredential and calls the model, so that identity needs the Azure AI User role on the Foundry resource.
// The identities only exist after the agents are deployed: 02_create-hostedagentroles.ps1 reads their ids and passes them here.

@description('Existing Foundry resource (Azure AI Services account) name.')
param foundryName string

@description('Principal ids of the hosted agents, read from Foundry after deployment.')
param principalIds array

// Built-in role: Azure AI User.
var azureAiUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

resource roles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in principalIds: {
  name: guid(foundry.id, principalId, azureAiUserRoleId)
  scope: foundry
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAiUserRoleId)
  }
}]
