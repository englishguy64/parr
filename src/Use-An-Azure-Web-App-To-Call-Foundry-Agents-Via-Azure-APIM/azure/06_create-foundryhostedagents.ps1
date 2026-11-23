# Creates the three Foundry Hosted Agents (one orchestrator, order lookup and policy check) from images in the registry.
# Run 05_create-acr.ps1 and push the images (orchestrator:latest, order-lookup:latest, policy-check:latest) first,
# and run this before 03_create-foundry.ps1 -LockDown.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$FoundryName = "${env:TENANT_PREFIX}",
  [string]$ProjectName = "${env:TENANT_PREFIX}-FoundryProject",
  [string]$AcrName = (($env:TENANT_PREFIX -replace '[^a-zA-Z0-9]', '').ToLower() + 'acr'),
  [string]$StorageAccountName = (($env:TENANT_PREFIX -replace '[^a-zA-Z0-9]', '').ToLower() + 'files')
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
if ($StorageAccountName.Length -gt 24) { $StorageAccountName = $StorageAccountName.Substring(0, 24) }   # same name 07_create-backendapi.ps1 uses

# deploymentScripts needs this provider (it runs in an Azure Container Instance).
az provider register --namespace Microsoft.ContainerInstance --wait

$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_foundryhostedagents.bicep" `
  -p foundryName=$FoundryName projectName=$ProjectName acrLoginServer="$AcrName.azurecr.io" storageAccountName=$StorageAccountName `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Hosted agent deployment failed.' }

"Created hosted agents: $($out.hostedAgentNames.value -join ', ')"
