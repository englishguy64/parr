# Creates the two Azure Key Vaults for the BankID relying party certificates: one for test and one for production.
# Names are built from the RECIPE_PREFIX environment variable, a unique prefix for this recipe such as thunderbirdsarego, as in the
# Use-An-Azure-Web-App recipe (use a different prefix from that recipe if you deploy both):
#   resource group <prefix>-rg1 (you create it yourself, the scripts only use it)     plan <prefix>-plan
#   Backend API    <prefix>-api      web site <prefix>-web      vaults <prefix, 15 characters>-bid-test and -bid-prod
# Everything is created in the region of the resource group. Pass a parameter such as -ResourceGroup to choose a name yourself.
#
# The test certificate is uploaded to the test vault by 02_upload-test-certificate-to-keyvault.ps1.
# The production certificate is NOT uploaded by any script. You upload it by hand to the production vault, see the README.
param(
  [string]$ResourceGroup = "${env:RECIPE_PREFIX}-rg1",
  [string]$TestKeyVaultName = (((("${env:RECIPE_PREFIX}".ToLower()) -replace '[^a-z0-9]', '') -replace '^(.{1,15}).*$', '$1') + '-bid-test'),
  [string]$ProductionKeyVaultName = (((("${env:RECIPE_PREFIX}".ToLower()) -replace '[^a-z0-9]', '') -replace '^(.{1,15}).*$', '$1') + '-bid-prod')
)
$ErrorActionPreference = 'Stop'
if (-not $env:RECIPE_PREFIX) { throw 'Set the RECIPE_PREFIX environment variable first, for example:  $env:RECIPE_PREFIX = ''thunderbirdsarego''' }

if ($TestKeyVaultName -eq $ProductionKeyVaultName) { throw 'The test and production vaults must have different names.' }

# The tenant and subscription are the ones you are signed in to with az login. Nothing is set by hand.
$account = az account show --query "{tenantId:tenantId, subscriptionId:id, subscription:name, user:user.name}" -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $account) { throw 'Run az login first.' }
"Signed in as $($account.user)"
"Tenant:       $($account.tenantId)"
"Subscription: $($account.subscription) ($($account.subscriptionId))"

# The person who runs this script gets the Key Vault Certificates Officer role on both vaults: the test vault so that
# 02_upload-test-certificate-to-keyvault.ps1 can upload, and the production vault so that you can upload the production certificate by hand.
$uploaderId = az ad signed-in-user show --query id -o tsv
if ($LASTEXITCODE -ne 0 -or -not $uploaderId) { throw 'Could not read your object id. Run az login first.' }

# You create the resource group by hand (az group create). Its name is <prefix>-rg1. The scripts only use it. The resources are
# created in its region and in the tenant and subscription you are signed in to with az login.
if ((az group exists -n $ResourceGroup) -ne 'true') {
  throw "Resource group $ResourceGroup does not exist. Create it first, for example:  az group create -n $ResourceGroup -l <region>"
}
$Location = az group show -n $ResourceGroup --query location -o tsv
"Resource group: $ResourceGroup in $Location"

foreach ($vault in @($TestKeyVaultName, $ProductionKeyVaultName)) {
  $outputs = az deployment group create --subscription $account.subscriptionId -g $ResourceGroup `
    -f "$PSScriptRoot/create_keyvault.bicep" `
    -p keyVaultName=$vault location=$Location uploaderPrincipalId=$uploaderId uploaderPrincipalType=User `
    --query properties.outputs -o json | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0) { throw "Key Vault deployment failed for $vault." }
  "Key Vault: $($outputs.keyVaultName.value)   $($outputs.keyVaultUri.value)"
}

'Role assignments can take a few minutes to take effect. Then run 02_upload-test-certificate-to-keyvault.ps1 for the test certificate.'
'The production certificate is uploaded by hand to the production vault. See the README.'
