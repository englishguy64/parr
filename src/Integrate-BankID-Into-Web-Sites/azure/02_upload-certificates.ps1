# Puts the BankID relying party certificates in the Key Vault. The test certificate is required. The production
# certificate can be uploaded later, when your bank has issued it.
#
# The backend API reads two Key Vault certificates (and their private keys) by name:
#   bankid-test-certificate        the BankID test certificate (FPTestcert5) from the BankID test portal
#   bankid-production-certificate  the certificate ordered from your bank, as a PKCS#12 (.p12 or .pfx) file
#
# Example:
#   ./02_upload-certificates.ps1 -TestCertificatePath ./FPTestcert5_20240610.p12 -TestCertificatePassword (Read-Host -AsSecureString)
param(
  [string]$KeyVaultName = "${env:TENANT_PREFIX}-bankid-kv",
  [Parameter(Mandatory)][string]$TestCertificatePath,
  [Parameter(Mandatory)][securestring]$TestCertificatePassword,
  [string]$ProductionCertificatePath,
  [securestring]$ProductionCertificatePassword,
  [string]$TestCertificateName = 'bankid-test-certificate',
  [string]$ProductionCertificateName = 'bankid-production-certificate'
)
$ErrorActionPreference = 'Stop'
if (-not $KeyVaultName -or $KeyVaultName -eq '-bankid-kv') {
  throw 'Pass -KeyVaultName, or set the TENANT_PREFIX environment variable first.'
}

function ConvertTo-PlainText([securestring]$Secret) {
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
  try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Import-BankIdCertificate([string]$Name, [string]$Path, [securestring]$Password) {
  if (-not (Test-Path $Path)) { throw "Certificate file not found: $Path" }
  # The password is passed to az for the length of this call only. It is not written to a file.
  az keyvault certificate import --vault-name $KeyVaultName --name $Name --file $Path --password (ConvertTo-PlainText $Password) -o none
  if ($LASTEXITCODE -ne 0) {
    throw "Could not import $Name. If the file is encrypted with AES-256 and the import is refused, use the legacy .pfx from the BankID test download."
  }
  "Imported $Name"
}

Import-BankIdCertificate $TestCertificateName $TestCertificatePath $TestCertificatePassword

if ($ProductionCertificatePath) {
  if (-not $ProductionCertificatePassword) { throw 'Pass -ProductionCertificatePassword with -ProductionCertificatePath.' }
  Import-BankIdCertificate $ProductionCertificateName $ProductionCertificatePath $ProductionCertificatePassword
} else {
  'No production certificate given. Production mode stays unavailable until you upload one.'
}
