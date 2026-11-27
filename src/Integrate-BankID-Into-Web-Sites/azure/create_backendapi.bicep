// Backend API (App Service). The only part that talks to BankID. It reads the test certificate from Key Vault
// with its own managed identity. The App Service plan is created here and shared with the web site (create_webapp.bicep).
// Deploy create_keyvault.bicep first.

@description('Backend API web app name. Globally unique (becomes <name>.azurewebsites.net).')
param backendName string

@description('Web site name. Only used to build the one address the Backend API accepts calls from (CORS).')
param webAppName string

@description('App Service plan name.')
param appServicePlanName string

@description('App Service plan SKU. B1 is cheap and has Always On; use F1 for free but slower.')
param appServiceSku string = 'B1'

@description('Existing Key Vault created by create_keyvault.bicep.')
param keyVaultName string

@description('Name of the certificate imported by 02_upload-test-certificate.ps1.')
param certificateName string = 'fptestcert5'

@description('Compare the end user IP seen by this API with the one BankID reports. Turn off if phone and browser use different networks.')
param checkIp bool = true

param location string = resourceGroup().location

// Built-in role: Key Vault Secrets User (read the certificate with its private key as a secret).
var secretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource vault 'Microsoft.KeyVault/vaults@2024-11-01' existing = {
  name: keyVaultName
}

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: appServicePlanName
  location: location
  sku: { name: appServiceSku }
  kind: 'linux'
  properties: { reserved: true }
}

resource backend 'Microsoft.Web/sites@2024-04-01' = {
  name: backendName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        // Test environment only. The root CA file ships with the app (certs/).
        { name: 'BANKID_URL', value: 'https://appapi2.test.bankid.com/rp/v6.0/' }
        { name: 'BANKID_KEYVAULT_URI', value: vault.properties.vaultUri }
        { name: 'BANKID_CERTIFICATE_NAME', value: certificateName }
        { name: 'BANKID_CHECK_IP', value: string(checkIp) }
        { name: 'WEBSITE_ORIGIN', value: 'https://${webAppName}.azurewebsites.net' }
      ]
    }
  }
}

resource backendReadsCertificate 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, backend.id, secretsUserRoleId)
  scope: vault
  properties: {
    principalId: backend.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRoleId)
  }
}

output appServicePlanName string = plan.name
output backendUrl string = 'https://${backend.properties.defaultHostName}'
