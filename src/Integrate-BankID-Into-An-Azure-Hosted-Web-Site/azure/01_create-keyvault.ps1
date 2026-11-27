# Creates the resource group and the Key Vault that will hold the BankID TEST certificate. Run 02_upload-test-certificate.ps1 next.
# Add -PreviewOnly to see what would change (az what-if) without creating anything.
param(
  [string]$ResourceGroup = "${env:RECEIPE_PREFIX}-bankid-rg",
  [string]$KeyVaultName = "${env:RECEIPE_PREFIX}-bankid-kv",
  [string]$Location = 'germanywestcentral',
  [switch]$PreviewOnly
)
if (-not $env:RECEIPE_PREFIX) { throw 'Set the RECEIPE_PREFIX environment variable first, for example:  $env:RECEIPE_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
# Key Vault names: 3 to 24 characters.
if ($KeyVaultName.Length -gt 24) { $KeyVaultName = $KeyVaultName.Substring(0, 24).TrimEnd('-') }

# Reuse the resource group if it already exists (even in another region), otherwise create it.
if ((az group exists -n $ResourceGroup) -eq 'true') {
  "Resource group $ResourceGroup already exists, continuing."
} else {
  az group create -n $ResourceGroup -l $Location -o none
  if ($LASTEXITCODE -ne 0) { throw 'Resource group creation failed.' }
}

# The signed in person gets Key Vault Certificates Officer so 02_upload-test-certificate.ps1 can import the certificate.
$me = az ad signed-in-user show --query id -o tsv
if ($LASTEXITCODE -ne 0) { throw 'Could not read the signed in user. Run az login first.' }

$template = @('-g', $ResourceGroup, '-f', "$PSScriptRoot/create_keyvault.bicep", '-p', "keyVaultName=$KeyVaultName", "uploaderObjectId=$me", "location=$Location")
if ($PreviewOnly) { az deployment group what-if @template; return }

$out = az deployment group create @template --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Key Vault deployment failed.' }
"KEY_VAULT=$($out.keyVaultName.value)   (next: 02_upload-test-certificate.ps1)"
