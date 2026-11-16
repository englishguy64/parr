# Creates the resource group that every other script deploys into. Run 02_create-network.ps1 next.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$Location = 'germanywestcentral'
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
az deployment sub create -l $Location `
  -f "$PSScriptRoot/create_resourcegroup.bicep" `
  -p resourceGroupName=$ResourceGroup location=$Location -o none
if ($LASTEXITCODE -ne 0) { throw 'Resource group deployment failed.' }
"Created resource group $ResourceGroup in $Location"
