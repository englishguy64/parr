# Gives the two hosted agents' identities the Azure AI User role on the Foundry resource, so they can call the chat model.
# Run it after 01_deploy-hostedagents.ps1. The agents' identities only exist once the agents are deployed.
# Role assignments can take a few minutes to take effect.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$FoundryName = "${env:TENANT_PREFIX}",
  [string]$ProjectName = "${env:TENANT_PREFIX}-FoundryProject",
  [string[]]$AgentNames = @('agui-support', 'agui-research')
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''englishguy64-18Nov''' }
$ErrorActionPreference = 'Stop'

$endpoint = "https://$FoundryName.services.ai.azure.com/api/projects/$ProjectName"
$principalIds = @()
foreach ($name in $AgentNames) {
  $id = az rest --method get --url "$endpoint/agents/${name}?api-version=v1" --resource https://ai.azure.com `
    --query instance_identity.principal_id -o tsv
  if ($LASTEXITCODE -ne 0 -or -not $id) { throw "Could not read the identity of agent '$name'. Is it deployed?" }
  "$name -> $id"
  $principalIds += $id
}

az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_hostedagentroles.bicep" `
  -p foundryName=$FoundryName principalIds="$(ConvertTo-Json -InputObject @($principalIds) -Compress)" -o none
if ($LASTEXITCODE -ne 0) { throw 'Role assignment deployment failed.' }

"Gave the agents the Azure AI User role on $FoundryName. Wait a few minutes before calling them."
