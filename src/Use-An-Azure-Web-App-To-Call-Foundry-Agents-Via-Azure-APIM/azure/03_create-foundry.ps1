# Deploys the Foundry resource, project, model and private endpoint, and grants the signed-in user access.
# Run 02_create-network.ps1 first. Agents are created by 04_create-foundrypromptagents.ps1.
#
# Order: 03_create-foundry.ps1  ->  04_create-foundrypromptagents.ps1  ->  03_create-foundry.ps1 -LockDown
# The agents are created from outside the VNet, so public access stays on until you pass -LockDown,
# which disables it so Foundry is reachable only through the private endpoint.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$FoundryName = "${env:TENANT_PREFIX}",
  [string]$ProjectName = "${env:TENANT_PREFIX}-FoundryProject",
  [string]$VnetName = 'vnet-ai',
  [switch]$LockDown
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
$access = if ($LockDown) { 'Disabled' } else { 'Enabled' }

$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_foundry.bicep" `
  -p foundryName=$FoundryName projectName=$ProjectName vnetName=$VnetName publicNetworkAccess=$access `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Foundry deployment failed.' }

# Let the current user create/run agents in the project (data-plane role).
$me = az ad signed-in-user show --query id -o tsv
$scope = az cognitiveservices account show -n $FoundryName -g $ResourceGroup --query id -o tsv
az role assignment create --assignee-object-id $me --assignee-principal-type User `
  --role 'Foundry User' --scope $scope -o none

"Public network access: $access"
"FOUNDRY_PROJECT_ENDPOINT=$($out.projectEndpoint.value)"
"FOUNDRY_MODEL_DEPLOYMENT=$($out.modelDeployment.value)"
