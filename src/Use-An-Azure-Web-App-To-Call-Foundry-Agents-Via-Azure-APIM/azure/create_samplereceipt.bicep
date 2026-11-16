// Uploads the sample receipt (hostedagents/order-lookup/sample-receipt.png) to Blob Storage so the agents can read it.
// Deploy create_backendapi.bicep first: it creates the storage account and the Foundry project's read access to it.
//
// Bicep has no resource type for a blob, so the file travels inside this template as base64 text (read from disk when
// the template is compiled) and a deploymentScript writes it to the container with az. The container is private and the
// account only accepts Entra ID: Order Lookup (running as the Foundry project identity) reads it with its own identity.
// Re-deploying uploads the file again, replacing the old one, so edit the PNG and re-run to change it.

@description('Storage account created by create_backendapi.bicep.')
param storageAccountName string

param location string = 'germanywestcentral'

@description('Changing this value forces the script to run again.')
param forceUpdateTag string = utcNow()

var containerName = 'samples'
var blobName = 'sample-receipt.png'

// The PNG as base64 text. An environment variable is limited in size, so it is passed in pieces and joined by the script.
var receiptBase64 = loadFileAsBase64('../hostedagents/order-lookup/sample-receipt.png')
var pieceSize = 20000
var pieceCount = (length(receiptBase64) + pieceSize - 1) / pieceSize
var receiptPieces = [for i in range(0, pieceCount): {
  name: 'RECEIPT_B64_${i}'
  value: substring(receiptBase64, i * pieceSize, min(pieceSize, length(receiptBase64) - i * pieceSize))
}]

// Built-in role: Storage Blob Data Contributor (lets the script write the blob with its identity).
var blobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {
  parent: storage
  name: 'default'
}

resource samples 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: containerName
  properties: { publicAccess: 'None' }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${storageAccountName}-upload-script-id'
  location: location
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, blobDataContributorRoleId)
  scope: storage
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobDataContributorRoleId)
  }
}

resource uploadReceipt 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: 'upload-sample-receipt'
  location: location
  kind: 'AzureCLI'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    azCliVersion: '2.67.0'
    forceUpdateTag: forceUpdateTag
    retentionInterval: 'PT1H'
    timeout: 'PT20M'
    cleanupPreference: 'OnSuccess'
    environmentVariables: concat([
      { name: 'STORAGE', value: storageAccountName }
      { name: 'CONTAINER', value: containerName }
      { name: 'BLOB', value: blobName }
      { name: 'PIECES', value: string(pieceCount) }
    ], receiptPieces)
    scriptContent: '''
      set -eu
      # Join the pieces and turn the text back into the PNG.
      i=0
      : > receipt.b64
      while [ "$i" -lt "$PIECES" ]; do
        printenv "RECEIPT_B64_$i" | tr -d '\n' >> receipt.b64
        i=$((i + 1))
      done
      base64 -d receipt.b64 > receipt.png
      echo "Decoded $(wc -c < receipt.png) bytes"
      # A real PNG starts with these bytes.
      [ "$(head -c 4 receipt.png | tail -c 3)" = "PNG" ] || { echo "Not a PNG file"; exit 1; }

      # Retry: the role assignment can take a few minutes to take effect.
      for attempt in $(seq 1 12); do
        if az storage blob upload --account-name "$STORAGE" --container-name "$CONTAINER" --name "$BLOB" \
             --file receipt.png --content-type image/png --overwrite true --auth-mode login --only-show-errors -o none; then
          echo "Uploaded $CONTAINER/$BLOB to $STORAGE"
          exit 0
        fi
        echo "Attempt $attempt failed, waiting for access to take effect"
        sleep 30
      done
      echo "Upload failed"
      exit 1
    '''
  }
  dependsOn: [roleAssignment, samples]
}

output sampleReceiptUrl string = '${storage.properties.primaryEndpoints.blob}${containerName}/${blobName}'
