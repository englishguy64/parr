# Deploys the BankID TEST certificate to the test Key Vault.
#
# The test certificate is a public test credential that BankID publishes for everyone: the file FPTestcert5_20240610.p12
# ("FP Testcert 5", issued by "Testbank A RP CA v1 for BankID Test") from the BankID test portal. Its password is also
# published by BankID, qwerty123, so the password and the Key Vault name are written below. They are not secrets and they only
# work against BankID's test servers. The production certificate is different: it comes from your bank, it is secret, and you
# upload it by hand to the production Key Vault. It never passes through a script, a Bicep file or an environment variable.
#
#   RECIPE_PREFIX                   names the test vault, as in 01_create-keyvault.ps1
#   BANKID_TEST_CERTIFICATE_PATH    where you saved FPTestcert5_20240610.p12, from the zip on the BankID test portal
#                                   https://developers.bankid.com/test-portal/test-information
param(
  [string]$TestKeyVaultName = (((("${env:RECIPE_PREFIX}".ToLower()) -replace '[^a-z0-9]', '') -replace '^(.{1,15}).*$', '$1') + '-bid-test'),
  [string]$TestCertificatePath = $env:BANKID_TEST_CERTIFICATE_PATH,
  # Public values. The name is the name of the certificate in the Key Vault, and 03_create-backendapi.ps1 gives the same name to the Backend API.
  [string]$TestCertificateName = 'fptestcert5',
  [string]$TestCertificatePassword = 'qwerty123'
)
$ErrorActionPreference = 'Stop'
if (-not $env:RECIPE_PREFIX) { throw 'Set the RECIPE_PREFIX environment variable first, for example:  $env:RECIPE_PREFIX = ''thunderbirdsarego''' }
if (-not $TestCertificatePath) { throw 'Set BANKID_TEST_CERTIFICATE_PATH to where you saved FPTestcert5_20240610.p12, the file from the zip on the BankID test portal.' }
if (-not (Test-Path $TestCertificatePath)) { throw "Certificate file not found: $TestCertificatePath" }

az keyvault certificate import --vault-name $TestKeyVaultName --name $TestCertificateName --file $TestCertificatePath --password $TestCertificatePassword -o none
if ($LASTEXITCODE -ne 0) {
  throw "Could not import $TestCertificateName. If the file is encrypted with AES-256 and the import is refused, use the legacy .pfx from the BankID test download."
}
"Imported $TestCertificateName into $TestKeyVaultName"
'The production certificate is not uploaded by this script. Upload it by hand to the production Key Vault, see the README.'
