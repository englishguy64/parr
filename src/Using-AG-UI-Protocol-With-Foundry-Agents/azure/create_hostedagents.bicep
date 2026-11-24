// Deploys the AG-UI recipe's Foundry Hosted Agents FROM SOURCE: no container and no registry.
//
// Each agent's source (a flat zip of the .csproj and .cs files, made by 01_deploy-hostedagents.ps1) arrives as a base64
// parameter. A deploymentScript uploads it to the Agent Service REST API as a code package. Foundry then runs
// `dotnet restore` and `dotnet publish` itself. The agent is registered with the Responses protocol at version 2.0.0, which is
// the version the Microsoft.Agents.AI.Foundry.Hosting package serves. (The Foundry Toolkit wizard registered 1.0.0, so calls
// failed with "requires responses protocol v2.0.0".)
//
// Same approach as the other recipe's create_foundryhostedagents.bicep: a deploymentScript calls the Agent Service REST API.
// Hosted Agents are a preview feature: the request shape below follows the code-deploy REST API (api-version v1), so check it
// against the current Foundry documentation before relying on it. Deploy while Foundry still allows public access.
//
// Run through 01_deploy-hostedagents.ps1, which builds the zips and passes the parameters.

@description('Existing Foundry resource (Azure AI Services account) name.')
param foundryName string

@description('Existing Foundry project name.')
param projectName string

@description('Chat model deployment the agents use, set as AZURE_AI_MODEL_DEPLOYMENT_NAME.')
param modelDeployment string = 'gpt-4.1-mini'

@description('The agents to deploy. name: agent name (must start with agui-). entryDll: the published assembly, for example agui-support.dll. description: shown in Foundry. zipBase64 and sha256: the flat source zip and its SHA-256 (lower case hex).')
param agents array

param location string = resourceGroup().location

@description('Changing this value forces the script to run again.')
param forceUpdateTag string = utcNow()

// Built-in role: Azure AI User (data-plane access to create and run agents).
var azureAiUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${foundryName}-aguiagents-script-id'
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

resource deployAgents 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: 'deploy-agui-hosted-agents'
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
    timeout: 'PT30M'
    cleanupPreference: 'OnSuccess'
    environmentVariables: [
      { name: 'PROJECT_ENDPOINT', value: 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}' }
      { name: 'MODEL', value: modelDeployment }
      { name: 'AGENTS_JSON', value: string(agents) }
    ]
    scriptContent: '''
      set -eu
      for attempt in $(seq 1 10); do
        TOKEN=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv) && break
        sleep 15
      done

      echo "$AGENTS_JSON" | jq -c '.[]' | while read -r AGENT_JSON; do
        NAME=$(echo "$AGENT_JSON" | jq -r .name)
        DLL=$(echo "$AGENT_JSON" | jq -r .entryDll)
        DESC=$(echo "$AGENT_JSON" | jq -r .description)
        SHA=$(echo "$AGENT_JSON" | jq -r .sha256)
        echo "$AGENT_JSON" | jq -r .zipBase64 | base64 -d > "$NAME.zip"

        # The zip must arrive unchanged: check its hash against the one computed on the PC.
        [ "$(sha256sum "$NAME.zip" | cut -d' ' -f1)" = "$SHA" ] || { echo "Zip for $NAME was altered in transit."; exit 1; }

        # The agent definition. protocol_versions responses 2.0.0 is what the hosting package serves.
        jq -nc --arg d "$DESC" --arg dll "$DLL" --arg m "$MODEL" \
          '{description: $d, definition: {kind: "hosted",
            protocol_versions: [{protocol: "responses", version: "2.0.0"}],
            cpu: "0.5", memory: "1.0Gi",
            code_configuration: {runtime: "dotnet_10", entry_point: ["dotnet", $dll], dependency_resolution: "remote_build"},
            environment_variables: {AZURE_AI_MODEL_DEPLOYMENT_NAME: $m}}}' > metadata.json

        # Retry: the script identity's role assignment can take a few minutes to propagate.
        for attempt in $(seq 1 12); do
          # Create. If the agent already exists (409) post to its own URL to add a new version instead.
          CODE=$(curl -s -o resp.json -w '%{http_code}' -X POST "$PROJECT_ENDPOINT/agents?api-version=v1" \
            -H "Authorization: Bearer $TOKEN" -H 'Accept: application/json' \
            -H "x-ms-agent-name: $NAME" -H "x-ms-code-zip-sha256: $SHA" \
            -F "metadata=@metadata.json;type=application/json" \
            -F "code=@$NAME.zip;type=application/zip;filename=$NAME.zip")
          if [ "$CODE" = "409" ]; then
            CODE=$(curl -s -o resp.json -w '%{http_code}' -X POST "$PROJECT_ENDPOINT/agents/$NAME?api-version=v1" \
              -H "Authorization: Bearer $TOKEN" -H 'Accept: application/json' \
              -H "x-ms-code-zip-sha256: $SHA" \
              -F "metadata=@metadata.json;type=application/json" \
              -F "code=@$NAME.zip;type=application/zip;filename=$NAME.zip")
          fi
          case "$CODE" in 200|201|202) break ;; esac
          echo "Attempt $attempt for $NAME returned HTTP $CODE: $(cat resp.json)"
          sleep 30
        done
        case "$CODE" in 200|201|202) ;; *) exit 1 ;; esac

        VERSION=$(jq -r '.versions.latest.version // .version' resp.json)
        echo "Uploaded $NAME, version $VERSION. Waiting for provisioning (remote build)..."

        # Poll until the version is active. A failed remote build shows the compile or restore error.
        for i in $(seq 1 120); do
          curl -s -H "Authorization: Bearer $TOKEN" "$PROJECT_ENDPOINT/agents/$NAME/versions/$VERSION?api-version=v1" > ver.json
          STATUS=$(jq -r '.status' ver.json)
          echo "  $NAME version $VERSION: $STATUS"
          [ "$STATUS" = "active" ] && break
          if [ "$STATUS" = "failed" ]; then echo "Provisioning failed: $(jq -c .error ver.json)"; exit 1; fi
          sleep 5
        done
        [ "$STATUS" = "active" ] || { echo "$NAME did not become active in time. Remote builds taking over 10 minutes: see the README."; exit 1; }
      done
    '''
  }
  dependsOn: [roleAssignment]
}

output agentNames array = [for a in agents: a.name]
