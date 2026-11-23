# Creates the vnet-ai virtual network (snet-web, snet-apim, snet-pe), the APIM network security group and the private DNS zones.
# Run 01_create-resourcegroup.ps1 first.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$Location = 'germanywestcentral',
  [string]$VnetName = 'vnet-ai'
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_network.bicep" `
  -p vnetName=$VnetName location=$Location -o none
if ($LASTEXITCODE -ne 0) { throw 'Network deployment failed.' }
"Created virtual network $VnetName in $ResourceGroup"
