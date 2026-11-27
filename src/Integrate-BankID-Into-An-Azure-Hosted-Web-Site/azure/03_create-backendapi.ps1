# Creates the App Service plan and the Backend API web app, and lets the Backend API read the certificate from Key Vault.
# Run 01 and 02 first. Deploy the code with 04_deploy-backendapi.ps1 next.
param(
  [string]$ResourceGroup = "${env:RECEIPE_PREFIX}-bankid-rg",
  [string]$BackendName = "${env:RECEIPE_PREFIX}-bankid-api",
  [string]$WebAppName = "${env:RECEIPE_PREFIX}-bankid-web",
  [string]$PlanName = "${env:RECEIPE_PREFIX}-bankid-plan",
  [string]$KeyVaultName = "${env:RECEIPE_PREFIX}-bankid-kv",
  [string]$PlanSku = 'B1',
  [string]$Location = 'germanywestcentral',
  [switch]$PreviewOnly
)
if (-not $env:RECEIPE_PREFIX) { throw 'Set the RECEIPE_PREFIX environment variable first, for example:  $env:RECEIPE_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
if ($KeyVaultName.Length -gt 24) { $KeyVaultName = $KeyVaultName.Substring(0, 24).TrimEnd('-') }

$template = @('-g', $ResourceGroup, '-f', "$PSScriptRoot/create_backendapi.bicep", '-p',
  "backendName=$BackendName", "webAppName=$WebAppName", "appServicePlanName=$PlanName", "keyVaultName=$KeyVaultName", "appServiceSku=$PlanSku", "location=$Location")
if ($PreviewOnly) { az deployment group what-if @template; return }

$out = az deployment group create @template --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Backend API deployment failed.' }
"BACKEND_API_URL=$($out.backendUrl.value)   (next: 04_deploy-backendapi.ps1)"
