// Tightens settings on the two App Services after everything is deployed and working.
// It changes only the settings listed here and leaves app settings, VNet integration and access restrictions alone.
// Deploy it last (after 09_deploy-backendapi.ps1 and 13_deploy-website.ps1): turning off basic authentication on the
// SCM site is why deployments must use Entra ID (az webapp deploy does, the same as the scripts here).
//
// What it sets, on the Backend API and on the website:
//   - TLS 1.2 minimum on the site and on the SCM (Kudu) site
//   - FTP and FTPS turned off, and the FTP publishing password switched off
//   - SCM basic-authentication (publishing password) switched off, so only Entra ID can deploy
//   - HTTP/2 on, remote debugging off
//   - Backend API only: the SCM site follows the same access restrictions as the main site (only API Management)
//
// Not done here, because they would redeploy a resource that takes a long time or breaks working access:
//   - APIM TLS/cipher settings (a change to the 30-60 minute Developer service)
//   - Foundry public network access: redeploy create_foundry.bicep with publicNetworkAccess = 'Disabled' once the
//     agents exist (see create_foundry.bicep)

@description('Backend API web app name (create_backendapi.bicep).')
param backendName string

@description('Website web app name (create_webapp.bicep).')
param webAppName string

@description('Turn off basic authentication (publishing password) on the SCM site. Deployments then need Entra ID, which az webapp deploy uses.')
param disableScmBasicAuth bool = true

resource backend 'Microsoft.Web/sites@2024-04-01' existing = {
  name: backendName
}

resource web 'Microsoft.Web/sites@2024-04-01' existing = {
  name: webAppName
}

resource backendConfig 'Microsoft.Web/sites/config@2024-04-01' = {
  parent: backend
  name: 'web'
  properties: {
    minTlsVersion: '1.2'
    scmMinTlsVersion: '1.2'
    ftpsState: 'Disabled'
    http20Enabled: true
    remoteDebuggingEnabled: false
    scmIpSecurityRestrictionsUseMain: true // the SCM site accepts only API Management too
  }
}

resource webConfig 'Microsoft.Web/sites/config@2024-04-01' = {
  parent: web
  name: 'web'
  properties: {
    minTlsVersion: '1.2'
    scmMinTlsVersion: '1.2'
    ftpsState: 'Disabled'
    http20Enabled: true
    remoteDebuggingEnabled: false
  }
}

resource backendFtp 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: backend
  name: 'ftp'
  properties: { allow: false }
}

resource backendScm 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: backend
  name: 'scm'
  properties: { allow: !disableScmBasicAuth }
}

resource webFtp 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: web
  name: 'ftp'
  properties: { allow: false }
}

resource webScm 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: web
  name: 'scm'
  properties: { allow: !disableScmBasicAuth }
}
