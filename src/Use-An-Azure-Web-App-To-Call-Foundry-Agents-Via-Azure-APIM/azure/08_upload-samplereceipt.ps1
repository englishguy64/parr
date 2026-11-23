# Uploads hostedagents/order-lookup/sample-receipt.png to the "samples" container of the storage account.
# Run 07_create-backendapi.ps1 first (it creates the storage account). Re-run it after changing the PNG.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$StorageAccountName = (($env:TENANT_PREFIX -replace '[^a-zA-Z0-9]', '').ToLower() + 'files')
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
if ($StorageAccountName.Length -gt 24) { $StorageAccountName = $StorageAccountName.Substring(0, 24) }   # same name 07_create-backendapi.ps1 uses

# deploymentScripts needs this provider (it runs in an Azure Container Instance).
az provider register --namespace Microsoft.ContainerInstance --wait

$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_samplereceipt.bicep" `
  -p storageAccountName=$StorageAccountName `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Sample receipt upload failed.' }

# Let the signed-in user list and open the private blob (Storage Blob Data Reader). Needs Owner or User Access
# Administrator; if you don't have that, this is skipped with a warning and the upload above is unaffected.
$scope = az storage account show -g $ResourceGroup -n $StorageAccountName --query id -o tsv
$userId = az ad signed-in-user show --query id -o tsv
az role assignment create --assignee-object-id $userId --assignee-principal-type User --role 'Storage Blob Data Reader' --scope $scope -o none
if ($LASTEXITCODE -ne 0) { Write-Warning 'Could not grant you Storage Blob Data Reader, so you may not be able to list the blob yourself.' }
else { "Granted you Storage Blob Data Reader on $StorageAccountName (can take a few minutes to apply): az storage blob list --account-name $StorageAccountName -c samples --auth-mode login -o table" }

"SAMPLE_RECEIPT_URL=$($out.sampleReceiptUrl.value)   (private: only Entra identities with a role on the account can open it)"
