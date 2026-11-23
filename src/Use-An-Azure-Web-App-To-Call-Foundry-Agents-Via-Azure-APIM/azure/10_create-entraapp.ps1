# Registers the website's Entra app: a single-page application (the browser signs in with MSAL.js) that is also the
# API protected by API Management. Bicep (create_entraapp.bicep) creates the registration, redirect URIs and the
# access_as_user scope; this script then sets the identifier URI (api://<client id>), which needs the client id.
# There is no client secret: a browser can't keep one.
#
# You need permission to register applications in the tenant. Run it BEFORE the APIM script: APIM is given the client
# id so it can check tokens. The script prints the two values the website needs.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$Location = 'germanywestcentral',
  [string]$DisplayName = 'Foundry Agents Web',
  [string]$UniqueName = "${env:TENANT_PREFIX}-web",
  [string]$WebAppName = "${env:TENANT_PREFIX}-web",
  [switch]$NoLocalhost
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
$localhost = if ($NoLocalhost) { 'false' } else { 'true' }

# A deployment needs a resource group to run in; this is a no-op if it already exists.
az group create -n $ResourceGroup -l $Location -o none

$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_entraapp.bicep" `
  -p displayName=$DisplayName uniqueName=$UniqueName webAppHostName="$WebAppName.azurewebsites.net" includeLocalhost=$localhost `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'App registration failed. Check you are allowed to register applications.' }

$clientId = $out.clientId.value
$tenantId = az account show --query tenantId -o tsv

# The identifier URI is how the scope is named in a token request: api://<client id>/access_as_user.
az ad app update --id $clientId --identifier-uris "api://$clientId"
if ($LASTEXITCODE -ne 0) { throw 'Could not set the identifier URI.' }

"Registered '$DisplayName'. Redirect URIs: $($out.redirectUris.value -join ', ')"
""
"ENTRA_TENANT_ID=$tenantId"
"ENTRA_CLIENT_ID=$clientId"
"API scope: api://$clientId/access_as_user"
""
"No secret is needed. Next: 11_create-azureapim.ps1 (it finds this app by name), then 12_create-webapp.ps1."
"To run the page locally, set ENTRA_TENANT_ID and ENTRA_CLIENT_ID (and APIM_BASE_URL) as environment variables."
