// An Azure Key Vault that holds the BankID relying party certificates, one for test and one for production.
//
// The vault uses Azure RBAC, not access policies. Two roles are handed out:
//  - Key Vault Certificates Officer to whoever uploads the certificates (02_upload-certificates.ps1)
//  - Key Vault Secrets User to the identity of the backend API. Key Vault keeps a certificate with its private key as a secret
//    of the same name, and the backend reads that secret. It cannot change or delete anything.
// The certificates themselves are uploaded by 02_upload-certificates.ps1, so no certificate or password is in this file.

@description('Name of the Key Vault. 3 to 24 characters, letters, digits and hyphens. It must be unique in Azure.')
@minLength(3)
@maxLength(24)
param keyVaultName string

@description('Azure region.')
param location string = resourceGroup().location

@description('Object id of the person (or pipeline) that uploads the certificates.')
param uploaderPrincipalId string

@description('Type of the uploader: User or ServicePrincipal.')
@allowed([ 'User', 'ServicePrincipal' ])
param uploaderPrincipalType string = 'User'

@description('Principal ids that may read the certificates: the managed identity of the backend API. Leave empty when you only run the backend on your PC with az login.')
param backendPrincipalIds array = []

// Built-in roles.
var certificatesOfficerRoleId = 'a4417e6f-fecd-4de8-b567-7b0420556985'
var secretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

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

resource backendRoles 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for principalId in backendPrincipalIds: {
  name: guid(vault.id, principalId, secretsUserRoleId)
  scope: vault
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRoleId)
  }
}]

output keyVaultName string = vault.name
output keyVaultUri string = vault.properties.vaultUri
