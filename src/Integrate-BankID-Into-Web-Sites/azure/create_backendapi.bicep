// The Backend API (App Service): the only part that talks to BankID. It also creates the App Service plan that the web site
// (create_webapp.bicep) shares, so deploy this first. Its application settings are the environment variables the backend
// reads (see backendapi/BankIdOptions.cs). Every value is a parameter and none has a default.
//
// The Backend API has a system assigned identity. It gets the Key Vault Secrets User role on both vaults, so it can read the two
// BankID certificates without any password or key in the application settings.

@description('Name of the Backend API. It becomes https://<name>.azurewebsites.net and must be unique in Azure.')
param backendName string

@description('Name of the App Service plan. The Backend API and the web site share it, so this template creates it.')
param planName string

@description('App Service plan size, for example B1.')
param skuName string

@description('The existing Key Vault that holds the test certificate.')
param testKeyVaultName string

@description('The existing Key Vault that holds the production certificate. You upload that certificate by hand.')
param productionKeyVaultName string

@description('Azure region.')
param location string

@description('The address of the web site in Azure. It is the only origin that may call this API from a browser, and BankID returns a phone user to it after the BankID app.')
param webSiteUrl string

@description('BankID test endpoint.')
param testUrl string

@description('Name of the Key Vault certificate for the test environment.')
param testCertificateName string

@description('Path of the BankID SSL root CA (PEM) for test, relative to the web app root.')
param testRootCaPath string

@description('true or false: require the ip from BankID to match the ip of the browser, in test.')
param testCheckIp string

@description('BankID production endpoint.')
param productionUrl string

@description('Name of the Key Vault certificate for the production environment.')
param productionCertificateName string

@description('Path of the BankID SSL root CA (PEM) for production, relative to the web app root.')
param productionRootCaPath string

@description('true or false: require the ip from BankID to match the ip of the browser, in production.')
param productionCheckIp string

// Built-in role: Key Vault Secrets User.
var secretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource testVault 'Microsoft.KeyVault/vaults@2024-11-01' existing = {
  name: testKeyVaultName
}

resource productionVault 'Microsoft.KeyVault/vaults@2024-11-01' existing = {
  name: productionKeyVaultName
}

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: planName
  location: location
  kind: 'linux'
  sku: {
    name: skuName
  }
  properties: {
    reserved: true
  }
}

resource site 'Microsoft.Web/sites@2024-04-01' = {
  name: backendName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      http20Enabled: true
      alwaysOn: true
    }
  }
}

resource settings 'Microsoft.Web/sites/config@2024-04-01' = {
  parent: site
  name: 'appsettings'
  properties: {
    BANKID_WEBSITE_URL: webSiteUrl
    BANKID_TEST_URL: testUrl
    BANKID_TEST_KEYVAULT_URI: testVault.properties.vaultUri
    BANKID_TEST_CERTIFICATE_NAME: testCertificateName
    BANKID_TEST_ROOT_CA_PATH: testRootCaPath
    BANKID_TEST_CHECK_IP: testCheckIp
    BANKID_PRODUCTION_URL: productionUrl
    BANKID_PRODUCTION_KEYVAULT_URI: productionVault.properties.vaultUri
    BANKID_PRODUCTION_CERTIFICATE_NAME: productionCertificateName
    BANKID_PRODUCTION_ROOT_CA_PATH: productionRootCaPath
    BANKID_PRODUCTION_CHECK_IP: productionCheckIp
    SCM_DO_BUILD_DURING_DEPLOYMENT: 'false'
  }
}

resource secretsUserTest 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(testVault.id, site.id, secretsUserRoleId)
  scope: testVault
  properties: {
    principalId: site.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRoleId)
  }
}

resource secretsUserProduction 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(productionVault.id, site.id, secretsUserRoleId)
  scope: productionVault
  properties: {
    principalId: site.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRoleId)
  }
}

output backendName string = site.name
output backendUrl string = 'https://${site.properties.defaultHostName}'
output defaultHostName string = site.properties.defaultHostName
output principalId string = site.identity.principalId
