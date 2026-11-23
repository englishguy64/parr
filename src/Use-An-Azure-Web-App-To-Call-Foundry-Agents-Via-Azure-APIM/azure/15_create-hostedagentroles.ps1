# Gives the Hosted Agents the roles Order Lookup needs to read receipts (Document Intelligence and the receipt blob).
# Run 06_create-foundryhostedagents.ps1 first. Run this script again after you create a new version of Order Lookup,
# because every new version gets a new identity.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$FoundryName = "${env:TENANT_PREFIX}",
  [string]$ProjectName = "${env:TENANT_PREFIX}-FoundryProject",
  [string]$StorageAccountName = (($env:TENANT_PREFIX -replace '[^a-zA-Z0-9]', '').ToLower() + 'files'),
  [string]$OrderLookupAgent = "${env:TENANT_PREFIX}-order-lookup"
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
if ($StorageAccountName.Length -gt 24) { $StorageAccountName = $StorageAccountName.Substring(0, 24) }   # same name 07_create-backendapi.ps1 uses

# The identity of the Order Lookup version that is running now.
$token = az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv
$agent = Invoke-RestMethod "https://$FoundryName.services.ai.azure.com/api/projects/$ProjectName/agents/${OrderLookupAgent}?api-version=v1" -Headers @{ Authorization = "Bearer $token" }
$principalId = $agent.versions.latest.instance_identity.principal_id
if (-not $principalId) { throw "Could not find the identity of '$OrderLookupAgent'. Run 06_create-foundryhostedagents.ps1 first." }
"Order Lookup version $($agent.versions.latest.version) runs as $principalId"

az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_hostedagentroles.bicep" `
  -p foundryName=$FoundryName projectName=$ProjectName storageAccountName=$StorageAccountName orderLookupPrincipalId=$principalId `
  -o none
if ($LASTEXITCODE -ne 0) { throw 'Role deployment failed.' }

"Roles granted. They can take up to about 10 minutes to take effect."
