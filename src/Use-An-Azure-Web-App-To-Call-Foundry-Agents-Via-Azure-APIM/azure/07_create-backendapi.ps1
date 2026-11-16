# Deploys the Backend API (App Service) into snet-api and lets it call Foundry with its managed identity.
# Run 02_create-network.ps1 and 03_create-foundry.ps1 first, then run 08_upload-samplereceipt.ps1 and deploy the code with 09_deploy-backendapi.ps1.
# It also creates the shared App Service plan and the storage account that holds the sample receipt.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$BackendName = "${env:TENANT_PREFIX}-api",
  [string]$PlanName = "${env:TENANT_PREFIX}-plan",
  [string]$StorageAccountName = (($env:TENANT_PREFIX -replace '[^a-zA-Z0-9]', '').ToLower() + 'files'),
  [string]$PlanSku = 'B1',
  [string]$FoundryName = "${env:TENANT_PREFIX}",
  [string]$ProjectName = "${env:TENANT_PREFIX}-FoundryProject",
  [string]$VnetName = 'vnet-ai'
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
# Storage account names: 3 to 24 lowercase letters and numbers.
if ($StorageAccountName.Length -gt 24) { $StorageAccountName = $StorageAccountName.Substring(0, 24) }
$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_backendapi.bicep" `
  -p backendName=$BackendName appServicePlanName=$PlanName storageAccountName=$StorageAccountName appServiceSku=$PlanSku foundryName=$FoundryName projectName=$ProjectName vnetName=$VnetName `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Backend API deployment failed.' }

"STORAGE_ACCOUNT=$($out.storageAccountName.value)   (the sample receipt goes here: run 08_upload-samplereceipt.ps1 next)"
"BACKEND_API_URL=$($out.backendUrl.value)   (only reachable from API Management)"
