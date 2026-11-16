// Creates the two prompt agents in an existing Microsoft Foundry project (same as csharp/Program.cs).
// Agents are a Foundry data-plane object, not an ARM resource, so a deploymentScript calls the
// Agent Service REST API using a user-assigned managed identity that holds the 'Azure AI User' role.
// Deploy main.bicep first.

@description('Existing Foundry resource (Azure AI Services account) name.')
param foundryName string

@description('Existing Foundry project name.')
param projectName string

@description('Chat model deployment the agents use.')
param modelDeploymentName string = 'gpt-4.1-mini'

// Agent name -> instructions. Names are built from foundryName (the TENANT_PREFIX).
var agents = {
  '${foundryName}-agentone': 'You are a concise, friendly English assistant. Answer in at most three sentences.'
  '${foundryName}-agenttwo': 'You are an English tutor. Correct the user\'s grammar and briefly explain why.'
}

param location string = 'germanywestcentral'

@description('Changing this value forces the script to run again.')
param forceUpdateTag string = utcNow()

// Built-in role: Azure AI User (data-plane access to create/run agents).
var azureAiUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${foundryName}-agents-script-id'
  location: location
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, identity.id, azureAiUserRoleId)
  scope: foundry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAiUserRoleId)
  }
}

resource createAgents 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: 'create-agents'
  location: location
  kind: 'AzureCLI'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    azCliVersion: '2.67.0'
    forceUpdateTag: forceUpdateTag
    retentionInterval: 'PT1H'
    timeout: 'PT20M'
    cleanupPreference: 'OnSuccess'
    environmentVariables: [
      { name: 'PROJECT_ENDPOINT', value: 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}' }
      { name: 'MODEL', value: modelDeploymentName }
      { name: 'AGENTS_JSON', value: string(agents) }
    ]
    scriptContent: '''
      set -eu
      for attempt in $(seq 1 10); do
        TOKEN=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv) && break
        sleep 15
      done
      echo "$AGENTS_JSON" | jq -r 'keys[]' | while read -r NAME; do
        BODY=$(echo "$AGENTS_JSON" | jq -c --arg n "$NAME" --arg m "$MODEL" \
          '{definition: {kind: "prompt", model: $m, instructions: .[$n]}}')
        # Retry: the role assignment can take a few minutes to propagate.
        for attempt in $(seq 1 12); do
          CODE=$(curl -s -o resp.json -w '%{http_code}' -X POST \
            "$PROJECT_ENDPOINT/agents/$NAME/versions?api-version=2025-11-15-preview" \
            -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d "$BODY")
          [ "$CODE" = "200" ] && break
          echo "Attempt $attempt for $NAME returned HTTP $CODE: $(cat resp.json)"
          sleep 30
        done
        [ "$CODE" = "200" ] || exit 1
        echo "Created agent $NAME (version $(jq -r .version resp.json)) using model $MODEL"
      done
    '''
  }
  dependsOn: [roleAssignment]
}

output agentNames array = objectKeys(agents)
