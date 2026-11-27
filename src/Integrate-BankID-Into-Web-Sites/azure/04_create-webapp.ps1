# Creates the web site in Azure: an App Service on the plan that 02_create-backendapi.ps1 made, with BACKEND_API_URL pointing
# at the Backend API. 05_deploy-webapp.ps1 deploys the code. Every setting is an environment variable and none has a default.
#
# Names are built from the RECIPE_PREFIX environment variable, a unique prefix for this recipe such as thunderbirdsarego, as in the
# Use-An-Azure-Web-App recipe (use a different prefix from that recipe if you deploy both):
#   resource group <prefix>-rg1 (you create it yourself, the scripts only use it)     plan <prefix>-plan
#   Backend API    <prefix>-api      web site <prefix>-web      vaults <prefix, 15 characters>-bid-test and -bid-prod
# Everything is created in the region of the resource group. Pass a parameter such as -ResourceGroup to choose a name yourself.
param(
  [string]$ResourceGroup = "${env:RECIPE_PREFIX}-rg1",
  [string]$PlanName = "${env:RECIPE_PREFIX}-plan",
  [string]$BackendName = "${env:RECIPE_PREFIX}-api",
  [string]$WebAppName = "${env:RECIPE_PREFIX}-web"
)
$ErrorActionPreference = 'Stop'
if (-not $env:RECIPE_PREFIX) { throw 'Set the RECIPE_PREFIX environment variable first, for example:  $env:RECIPE_PREFIX = ''thunderbirdsarego''' }

if ((az group exists -n $ResourceGroup) -ne 'true') { throw "Resource group $ResourceGroup does not exist." }
$Location = az group show -n $ResourceGroup --query location -o tsv
$backendApiUrl = "https://$BackendName.azurewebsites.net"

$outputs = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_webapp.bicep" `
  -p webAppName=$WebAppName planName=$PlanName backendApiUrl=$backendApiUrl location=$Location `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Web site deployment failed.' }

"Web site: $($outputs.webAppName.value)"
"Web site address: $($outputs.webAppUrl.value)"
"It calls the Backend API at $backendApiUrl"
'Then run 05_deploy-webapp.ps1.'
