# Deploys the website (App Service) on the shared plan. The page signs the user in with Entra in the browser and calls
# API Management directly, so the app settings only carry the APIM address and the Entra tenant and client ids.
# Run 07_create-backendapi.ps1 (it creates the plan), 10_create-entraapp.ps1 and 11_create-azureapim.ps1 first.
# Then deploy the page with 13_deploy-website.ps1.
#
# The Entra client id is looked up by the app's display name unless you pass -EntraClientId.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$WebAppName = "${env:TENANT_PREFIX}-web",
  [string]$PlanName = "${env:TENANT_PREFIX}-plan",
  [string]$ApimBaseUrl = "https://${env:TENANT_PREFIX}-apim.azure-api.net/api",
  [string]$DisplayName = 'Foundry Agents Web',
  [string]$EntraClientId = ''
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'

if (-not $EntraClientId) {
  $apps = @(az ad app list --display-name $DisplayName --query '[].appId' -o tsv)
  if ($apps.Count -eq 1) { $EntraClientId = $apps[0] }
  else { Write-Warning "Found $($apps.Count) Entra apps named '$DisplayName'. Sign-in is left off; run 10_create-entraapp.ps1 or pass -EntraClientId." }
}

$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_webapp.bicep" `
  -p webAppName=$WebAppName appServicePlanName=$PlanName apimBaseUrl=$ApimBaseUrl entraClientId=$EntraClientId `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Web app deployment failed.' }

"WEB_APP_URL=$($out.webAppUrl.value)"
