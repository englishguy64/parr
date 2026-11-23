# Deploys Azure API Management (Developer tier) into snet-apim in external VNet mode. The gateway is public: the browser
# calls it directly, APIM checks the user's Entra token, then routes /api/* to the Backend API through the VNet.
# Run 02_create-network.ps1, 07_create-backendapi.ps1 and 10_create-entraapp.ps1 first. This takes 30-60+ minutes.
#
# The Entra app's client id is looked up by its display name (the one 10_create-entraapp.ps1 created) unless you pass
# -ClientId. By default the gateway accepts browser calls from the website and from http://localhost:5080.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$ApimName = "${env:TENANT_PREFIX}-apim",
  [string]$BackendName = "${env:TENANT_PREFIX}-api",
  [string]$VnetName = 'vnet-ai',
  [Parameter(Mandatory)][string]$PublisherEmail,
  [string]$PublisherName = "${env:TENANT_PREFIX}",
  [string]$WebAppName = "${env:TENANT_PREFIX}-web",
  [string]$DisplayName = 'Foundry Agents Web',
  [string]$ClientId = '',
  [int]$RateLimitPerMinute = 60,
  [switch]$NoLocalhost
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'

if (-not $ClientId) {
  $apps = @(az ad app list --display-name $DisplayName --query '[].appId' -o tsv)
  if ($apps.Count -ne 1) { throw "Expected one Entra app named '$DisplayName' but found $($apps.Count). Run 10_create-entraapp.ps1 first, or pass -ClientId." }
  $ClientId = $apps[0]
}

# Origins the browser may call from (CORS). The array goes in a parameters file: az can't take JSON arrays inline reliably.
$origins = @("https://$WebAppName.azurewebsites.net")
if (-not $NoLocalhost) { $origins += 'http://localhost:5080' }
$paramFile = Join-Path ([System.IO.Path]::GetTempPath()) 'apim-origins.json'
@{ '$schema' = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'
   contentVersion = '1.0.0.0'
   parameters = @{ allowedOrigins = @{ value = $origins } } } | ConvertTo-Json -Depth 5 | Set-Content $paramFile -Encoding utf8

$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_azureapim.bicep" `
  -p "@$paramFile" `
  -p apimName=$ApimName backendName=$BackendName vnetName=$VnetName publisherEmail=$PublisherEmail publisherName=$PublisherName `
     apiClientId=$ClientId rateLimitPerMinute=$RateLimitPerMinute `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'APIM deployment failed.' }

"APIM_GATEWAY_URL=$($out.gatewayUrl.value)   (public)"
"APIM_API_BASE_URL=$($out.apiBaseUrl.value)"
"Allowed browser origins: $($origins -join ', ')"
"Next: 12_create-webapp.ps1 (it builds the same API address from the APIM name)."
