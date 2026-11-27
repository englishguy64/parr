// An Azure Key Vault that holds the BankID relying party certificates, one for test and one for production.
//
// The vault uses Azure RBAC, not access policies. Key Vault Certificates Officer is handed to whoever uploads the certificates
// (by hand, see the README). The web app that runs the backend API gets Key Vault Secrets User in create_webapp.bicep:
// Key Vault keeps a certificate with its private key as a secret of the same name, and the backend reads that secret.
// The certificates themselves are uploaded by hand, so no certificate or password is in this file.

@description('Name of the Key Vault. 3 to 24 characters, letters, digits and hyphens. It must be unique in Azure.')
@minLength(3)
@maxLength(24)
param keyVaultName string

@description('Azure region.')
param location string

@description('Object id of the person (or pipeline) that uploads the certificates.')
param uploaderPrincipalId string

@description('Type of the uploader: User or ServicePrincipal.')
@allowed([ 'User', 'ServicePrincipal' ])
param uploaderPrincipalType string

// Built-in role: Key Vault Certificates Officer.
var certificatesOfficerRoleId = 'a4417e6f-fecd-4de8-b567-7b0420556985'

resource vault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    // A deleted certificate cannot be purged for 90 days. A production certificate is worth protecting.
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
}

resource uploaderRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, uploaderPrincipalId, certificatesOfficerRoleId)
  scope: vault
  properties: {
    principalId: uploaderPrincipalId
    principalType: uploaderPrincipalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', certificatesOfficerRoleId)
  }
}

output keyVaultName string = vault.name
output keyVaultUri string = vault.properties.vaultUri
