# Creates a Basic Azure Container Registry for the Hosted Agent images.
# The registry has a public endpoint but accepts Entra ID authentication only (no admin user, no anonymous pull).
# Run 03_create-foundry.ps1 first. Then push the three images and run 06_create-foundryhostedagents.ps1.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$AcrName = (($env:TENANT_PREFIX -replace '[^a-zA-Z0-9]', '').ToLower() + 'acr'),
  [string]$FoundryName = "${env:TENANT_PREFIX}",
  [string]$ProjectName = "${env:TENANT_PREFIX}-FoundryProject"
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'

$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_acr.bicep" `
  -p acrName=$AcrName foundryName=$FoundryName projectName=$ProjectName `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Registry deployment failed.' }

"ACR_LOGIN_SERVER=$($out.loginServer.value)"
"Sign in with Entra ID, then push:  az acr build -r $AcrName -t orchestrator:latest <orchestrator folder>"
