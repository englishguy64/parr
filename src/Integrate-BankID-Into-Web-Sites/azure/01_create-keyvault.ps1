# Creates the Azure Key Vault that holds the BankID certificates, and the role assignments that go with it.
# Run it first. 02_upload-certificates.ps1 then puts the certificates in the vault.
#
# Example:
#   $env:TENANT_PREFIX = 'your-tenant-prefix'
#   ./01_create-keyvault.ps1
#   ./01_create-keyvault.ps1 -BackendPrincipalIds '<object id of the managed identity of the backend API>'
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$KeyVaultName = "${env:TENANT_PREFIX}-bankid-kv",
  [string]$Location = 'swedencentral',
  # Object ids that may read the certificates, for example the managed identity of the Azure web app that runs the backend.
  [string[]]$BackendPrincipalIds = @()
)
$ErrorActionPreference = 'Stop'
if ($ResourceGroup -eq '-rg1' -or $KeyVaultName -eq '-bankid-kv') {
  throw 'Pass -ResourceGroup and -KeyVaultName, or set the TENANT_PREFIX environment variable first.'
}

# The person who runs this script uploads the certificates, so they get the Key Vault Certificates Officer role.
$uploaderId = az ad signed-in-user show --query id -o tsv
if ($LASTEXITCODE -ne 0 -or -not $uploaderId) { throw 'Could not read your object id. Run az login first.' }

az group create -n $ResourceGroup -l $Location -o none
if ($LASTEXITCODE -ne 0) { throw 'Could not create the resource group.' }

$outputs = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_keyvault.bicep" `
  -p keyVaultName=$KeyVaultName location=$Location uploaderPrincipalId=$uploaderId `
     backendPrincipalIds="$(ConvertTo-Json -InputObject @($BackendPrincipalIds) -Compress)" `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Key Vault deployment failed.' }

"Key Vault: $($outputs.keyVaultName.value)"
"Key Vault URI: $($outputs.keyVaultUri.value)"
''
"Tell the backend API where the vault is:"
"  cd ../backendapi"
"  dotnet user-secrets set BankId:KeyVaultUri $($outputs.keyVaultUri.value)"
''
"Role assignments can take a few minutes to take effect. Then run 02_upload-certificates.ps1."
