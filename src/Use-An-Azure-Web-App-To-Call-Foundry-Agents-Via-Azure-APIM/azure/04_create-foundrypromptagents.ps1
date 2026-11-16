# Creates the two Foundry prompt agents by deploying ../azure/create_agents.bicep.
# Run 03_create-foundry.ps1 first (Foundry resource, project and model must already exist).
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$FoundryName = "${env:TENANT_PREFIX}",
  [string]$ProjectName = "${env:TENANT_PREFIX}-FoundryProject",
  [string]$ModelDeploymentName = 'gpt-4.1-mini'
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'

# deploymentScripts needs this provider (it runs in an Azure Container Instance).
az provider register --namespace Microsoft.ContainerInstance --wait

$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_foundrypromptagents.bicep" `
  -p foundryName=$FoundryName projectName=$ProjectName modelDeploymentName=$ModelDeploymentName `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Agent deployment failed.' }

"Created agents: $($out.agentNames.value -join ', ')"
