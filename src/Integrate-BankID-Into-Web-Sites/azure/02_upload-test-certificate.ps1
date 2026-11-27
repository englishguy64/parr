# Imports the BankID TEST relying party certificate (FPTestcert5) into the Key Vault. Run 03_create-backendapi.ps1 next.
# Get the public BankID test certificate (FPTestcert, a .p12 file) and its password from https://developers.bankid.com (search for "test certificate").
# The file and its password are public test material, but *.p12 and *.pfx are in .gitignore so they never get committed.
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingPlainTextForPassword', 'CertificatePassword', Justification = 'The BankID test certificate password is public test material.')]
param(
  [Parameter(Mandatory)][string]$CertificatePath,
  [Parameter(Mandatory)][string]$CertificatePassword, # the password BankID publishes with the test certificate
  [string]$KeyVaultName = "${env:RECEIPE_PREFIX}-bankid-kv",
  [string]$CertificateName = 'fptestcert5'
)
if (-not $env:RECEIPE_PREFIX) { throw 'Set the RECEIPE_PREFIX environment variable first, for example:  $env:RECEIPE_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
if ($KeyVaultName.Length -gt 24) { $KeyVaultName = $KeyVaultName.Substring(0, 24).TrimEnd('-') }
if (-not (Test-Path $CertificatePath)) { throw "$CertificatePath not found." }

az keyvault certificate import --vault-name $KeyVaultName -n $CertificateName -f $CertificatePath --password $CertificatePassword -o none
if ($LASTEXITCODE -ne 0) { throw 'Certificate import failed. Role assignments can take a minute to apply: wait and run again.' }
"Imported $CertificateName into $KeyVaultName."
