// Microsoft Entra app registration for the website, created with the Microsoft Graph Bicep extension.
//
// One registration plays two roles:
//   - A single-page application: the browser signs the user in with MSAL.js (authorization code flow with PKCE).
//     There is no client secret: a browser can't keep one.
//   - The API that API Management protects: it exposes the scope "access_as_user". The browser asks for an access
//     token for that scope, and APIM (apim-policy.xml) accepts only tokens issued for this app and scope.
//
// The identifier URI (api://<client id>) can only be set once the client id exists, so 10_create-entraapp.ps1 adds it
// after this deployment. The deploying user needs permission to register applications (the tenant setting
// "Users can register applications", or the Application Developer role).

extension microsoftGraphV1

@description('Display name of the app registration.')
param displayName string = 'Foundry Agents Web'

@description('Stable name for the app so redeploying updates it instead of creating a second copy.')
param uniqueName string

@description('Host name of the deployed website (without https://).')
param webAppHostName string

@description('Also allow sign-in when the page runs on your PC at http://localhost:5080.')
param includeLocalhost bool = true

var redirectUris = concat(
  ['https://${webAppHostName}/'],
  includeLocalhost ? ['http://localhost:5080/'] : []
)

resource app 'Microsoft.Graph/applications@v1.0' = {
  uniqueName: uniqueName
  displayName: displayName
  signInAudience: 'AzureADMyOrg' // this tenant only
  spa: {
    redirectUris: redirectUris
  }
  api: {
    requestedAccessTokenVersion: 2 // v2 tokens: issuer https://login.microsoftonline.com/<tenant>/v2.0, audience = client id
    oauth2PermissionScopes: [
      {
        id: guid(uniqueName, 'access_as_user')
        value: 'access_as_user'
        type: 'User'
        isEnabled: true
        adminConsentDisplayName: 'Use the Foundry agents API'
        adminConsentDescription: 'Lets the website call the Foundry agents API on behalf of the signed-in user.'
        userConsentDisplayName: 'Use the Foundry agents API'
        userConsentDescription: 'Lets the website call the Foundry agents API on your behalf.'
      }
    ]
  }
}

// The service principal is what lets users in this tenant sign in to the app.
resource servicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: app.appId
}

output clientId string = app.appId
output redirectUris array = redirectUris
