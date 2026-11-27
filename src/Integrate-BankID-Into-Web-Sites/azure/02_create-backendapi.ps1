# Creates the Backend API in Azure (App Service plan, the API, its application settings and the Key Vault roles).
# Run it after 01_create-keyvault.ps1. 03_deploy-backendapi.ps1 deploys the code, and 04_create-webapp.ps1 creates the web site. Every setting is an environment variable and none has a default.
# The application settings it creates are the environment variables the backend reads, with the same names.
#
# Names are built from the RECIPE_PREFIX environment variable, a unique prefix for this recipe such as thunderbirdsarego, as in the
# Use-An-Azure-Web-App recipe (use a different prefix from that recipe if you deploy both):
#   resource group <prefix>-rg1 (you create it yourself, the scripts only use it)     plan <prefix>-plan
#   Backend API    <prefix>-api      web site <prefix>-web      vaults <prefix, 15 characters>-bid-test and -bid-prod
# Everything is created in the region of the resource group. Pass a parameter such as -ResourceGroup to choose a name yourself.
#   The App Service plan is always B1, the small Basic tier. There is no setting for it
#   BANKID_TEST_URL                 https://appapi2.test.bankid.com/rp/v6.0/
#   BANKID_TEST_ROOT_CA_PATH        certs/Test-BankID-SSL-Root-CA-v1-Test.pem
#   BANKID_TEST_CHECK_IP            true or false
#   BANKID_PRODUCTION_URL           https://appapi2.bankid.com/rp/v6.0/
#   BANKID_PRODUCTION_CERTIFICATE_NAME, BANKID_PRODUCTION_ROOT_CA_PATH (certs/BankID-SSL-Root-CA-v1.pem), BANKID_PRODUCTION_CHECK_IP
param(
  [string]$ResourceGroup = "${env:RECIPE_PREFIX}-rg1",
  [string]$TestKeyVaultName = (((("${env:RECIPE_PREFIX}".ToLower()) -replace '[^a-z0-9]', '') -replace '^(.{1,15}).*$', '$1') + '-bid-test'),
  [string]$ProductionKeyVaultName = (((("${env:RECIPE_PREFIX}".ToLower()) -replace '[^a-z0-9]', '') -replace '^(.{1,15}).*$', '$1') + '-bid-prod'),
  [string]$PlanName = "${env:RECIPE_PREFIX}-plan",
  [string]$BackendName = "${env:RECIPE_PREFIX}-api",
  [string]$WebAppName = "${env:RECIPE_PREFIX}-web",
  [string]$WebSiteUrl,
  [string]$TestUrl = $env:BANKID_TEST_URL,
  [string]$TestCertificateName = 'fptestcert5',   # the public BankID test certificate FPTestcert5. You upload it by hand under this name
  [string]$TestRootCaPath = $env:BANKID_TEST_ROOT_CA_PATH,
  [string]$TestCheckIp = $env:BANKID_TEST_CHECK_IP,
  [string]$ProductionUrl = $env:BANKID_PRODUCTION_URL,
  [string]$ProductionCertificateName = $env:BANKID_PRODUCTION_CERTIFICATE_NAME,
  [string]$ProductionRootCaPath = $env:BANKID_PRODUCTION_ROOT_CA_PATH,
  [string]$ProductionCheckIp = $env:BANKID_PRODUCTION_CHECK_IP
)
$ErrorActionPreference = 'Stop'
$WebAppSku = 'B1'   # always B1, shared by the Backend API and the web site
if (-not $env:RECIPE_PREFIX) { throw 'Set the RECIPE_PREFIX environment variable first, for example:  $env:RECIPE_PREFIX = ''thunderbirdsarego''' }

if (-not $WebSiteUrl) { $WebSiteUrl = "https://$WebAppName.azurewebsites.net/" }
# You create the resource group by hand (az group create). Its name is <prefix>-rg1. The scripts only use it. The resources are
# created in its region and in the tenant and subscription you are signed in to with az login.
if ((az group exists -n $ResourceGroup) -ne 'true') {
  throw "Resource group $ResourceGroup does not exist. Create it first, for example:  az group create -n $ResourceGroup -l <region>"
}
$Location = az group show -n $ResourceGroup --query location -o tsv

$missing = @(
  @{ Name = 'BANKID_TEST_URL'; Value = $TestUrl },
  @{ Name = 'BANKID_TEST_ROOT_CA_PATH'; Value = $TestRootCaPath },
  @{ Name = 'BANKID_TEST_CHECK_IP'; Value = $TestCheckIp },
  @{ Name = 'BANKID_PRODUCTION_URL'; Value = $ProductionUrl },
  @{ Name = 'BANKID_PRODUCTION_CERTIFICATE_NAME'; Value = $ProductionCertificateName },
  @{ Name = 'BANKID_PRODUCTION_ROOT_CA_PATH'; Value = $ProductionRootCaPath },
  @{ Name = 'BANKID_PRODUCTION_CHECK_IP'; Value = $ProductionCheckIp }
) | Where-Object { -not $_.Value } | ForEach-Object { $_.Name }
if ($missing) { throw "Set these environment variables first, for example  `$env:BANKID_TEST_URL = 'https://appapi2.test.bankid.com/rp/v6.0/'  :  $($missing -join ', ')" }

$outputs = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_backendapi.bicep" `
  -p backendName=$BackendName planName=$PlanName skuName=$WebAppSku testKeyVaultName=$TestKeyVaultName productionKeyVaultName=$ProductionKeyVaultName location=$Location `
     webSiteUrl=$WebSiteUrl testUrl=$TestUrl testCertificateName=$TestCertificateName testRootCaPath=$TestRootCaPath testCheckIp=$TestCheckIp `
     productionUrl=$ProductionUrl productionCertificateName=$ProductionCertificateName productionRootCaPath=$ProductionRootCaPath `
     productionCheckIp=$ProductionCheckIp `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Backend API deployment failed.' }

"Backend API: $($outputs.backendName.value)"
"Backend API address: $($outputs.backendUrl.value)"
"Only $WebSiteUrl may call it from a browser."
'The roles on the Key Vaults can take a few minutes to take effect. Then run 03_deploy-backendapi.ps1.'
