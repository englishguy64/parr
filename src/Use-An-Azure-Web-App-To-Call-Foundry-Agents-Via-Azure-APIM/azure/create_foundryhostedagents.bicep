// Creates the three Foundry Hosted Agents: one orchestrator (support case coordinator) and two custom agents:
// order lookup (finds order status and details) and policy check (applies return and refund rules).
// Hosted Agents run your own container image (from the registry created by create_acr.bicep).
// The orchestrator is told the names of the other agents and delegates to them.
//
// Same approach as create_foundrypromptagents.bicep: a deploymentScript calls the Agent Service REST API.
// Hosted Agents are a preview feature: the request shape below follows the preview REST API
// (api-version 2025-11-15-preview), so check it against the current Foundry docs before relying on it.
// Push the three images to the registry first, and deploy while Foundry still allows public access.

@description('Existing Foundry resource (Azure AI Services account) name.')
param foundryName string

@description('Existing Foundry project name.')
param projectName string

@description('Registry login server, for example <name>acr.azurecr.io')
param acrLoginServer string

@description('Storage account that holds the sample receipt (created by create_backendapi.bicep). Order Lookup only downloads from it. Leave empty to allow any blob address.')
param storageAccountName string = ''

// Hosted Agent name -> image (repository:tag in the registry). Names are built from foundryName (the TENANT_PREFIX).
var hostedAgents = {
  '${foundryName}-orchestrator': 'orchestrator:latest'
  '${foundryName}-order-lookup': 'order-lookup:latest'
  '${foundryName}-policy-check': 'policy-check:latest'
}

// Name of the orchestrator agent. It receives the names of all the other agents as CUSTOM_AGENTS.
var orchestratorName = '${foundryName}-orchestrator'

param location string = 'germanywestcentral'

@description('Changing this value forces the script to run again.')
param forceUpdateTag string = utcNow()

// Built-in role: Azure AI User (data-plane access to create/run agents).
var azureAiUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${foundryName}-hostedagents-script-id'
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

resource createHostedAgents 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: 'create-hosted-agents'
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
      { name: 'ACR', value: acrLoginServer }
      { name: 'ORCHESTRATOR', value: orchestratorName }
      { name: 'DOC_ENDPOINT', value: 'https://${foundryName}.cognitiveservices.azure.com/' }
      { name: 'STORAGE', value: storageAccountName }
      { name: 'AGENTS_JSON', value: string(hostedAgents) }
    ]
    scriptContent: '''
      set -eu
      for attempt in $(seq 1 10); do
        TOKEN=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv) && break
        sleep 15
      done
      # The orchestrator learns the custom agent names so it can delegate to them.
      CUSTOM=$(echo "$AGENTS_JSON" | jq -r --arg o "$ORCHESTRATOR" 'keys | map(select(. != $o)) | join(",")')
      echo "$AGENTS_JSON" | jq -r 'keys[]' | while read -r NAME; do
        IMAGE=$(echo "$AGENTS_JSON" | jq -r --arg n "$NAME" '.[$n]')
        # Every agent can call Document Intelligence on the Foundry resource; the orchestrator also gets the agent names.
        ENVS=$(jq -nc --arg d "$DOC_ENDPOINT" --arg s "$STORAGE" '{DOCUMENT_INTELLIGENCE_ENDPOINT: $d, STORAGE_ACCOUNT: $s}')
        if [ "$NAME" = "$ORCHESTRATOR" ]; then ENVS=$(echo "$ENVS" | jq -c --arg c "$CUSTOM" '. + {CUSTOM_AGENTS: $c}'); fi
        BODY=$(jq -nc --arg i "$ACR/$IMAGE" --argjson e "$ENVS" \
          '{definition: {kind: "hosted", image: $i, cpu: "1", memory: "2Gi",
            container_protocol_versions: [{protocol: "responses", version: "2.0.0"}],
            environment_variables: $e}}')
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
        echo "Created hosted agent $NAME (version $(jq -r .version resp.json)) from $ACR/$IMAGE"
      done
    '''
  }
  dependsOn: [roleAssignment]
}

output hostedAgentNames array = objectKeys(hostedAgents)
