// Key Vault that holds the BankID TEST relying party certificate (FPTestcert5).
// Access is by Entra ID roles only (no access policies, no keys). Purge protection stays on, so a deleted vault
// keeps its name reserved until the retention period ends.

@description('Key Vault name. 3 to 24 characters, letters, numbers and hyphens, globally unique.')
@minLength(3)
@maxLength(24)
param keyVaultName string

@description('Object id of the person who uploads the certificate (gets Key Vault Certificates Officer). Leave empty to skip.')
param uploaderObjectId string = ''

param location string = resourceGroup().location

// Built-in role: Key Vault Certificates Officer (import and manage certificates).
var certificatesOfficerRoleId = 'a4417e6f-fecd-4de8-b567-7b0420556985'

resource vault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled' // cost saving demo: no private endpoint
  }
}

resource uploaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (uploaderObjectId != '') {
  name: guid(vault.id, uploaderObjectId, certificatesOfficerRoleId)
  scope: vault
  properties: {
    principalId: uploaderObjectId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', certificatesOfficerRoleId)
  }
}

output keyVaultName string = vault.name
output keyVaultUri string = vault.properties.vaultUri
