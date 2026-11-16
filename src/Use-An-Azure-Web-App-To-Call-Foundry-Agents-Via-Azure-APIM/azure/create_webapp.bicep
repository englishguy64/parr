// Website hosted in Azure App Service. It serves the page (../website) and tells it where APIM is and which Entra app
// to sign in to. The browser signs in with Entra (MSAL.js) and calls API Management directly: the website's server
// never handles the user's token or forwards requests, so it needs no VNet integration, subscription key or secret.
// Deploy create_backendapi.bicep first (it creates the shared App Service plan).

@description('Web app name. Must be globally unique (becomes <name>.azurewebsites.net).')
param webAppName string

@description('Name of the shared App Service plan created by create_backendapi.bicep.')
param appServicePlanName string

@description('APIM API address the browser calls (the apiBaseUrl output of create_azureapim.bicep).')
param apimBaseUrl string

@description('Client id of the Entra app registration the browser signs in to (create_entraapp.bicep). Leave empty to turn sign-in off.')
param entraClientId string = ''

@description('Entra tenant id.')
param tenantId string = tenant().tenantId

param location string = 'germanywestcentral'

// Shared with the Backend API: create_backendapi.bicep creates the plan, so deploy that first.
resource plan 'Microsoft.Web/serverfarms@2024-04-01' existing = {
  name: appServicePlanName
}

resource web 'Microsoft.Web/sites@2024-04-01' = {
  name: webAppName
  location: location
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      appSettings: [
        { name: 'APIM_BASE_URL', value: apimBaseUrl }
        { name: 'ENTRA_TENANT_ID', value: tenantId }
        { name: 'ENTRA_CLIENT_ID', value: entraClientId }
      ]
    }
  }
}

output webAppUrl string = 'https://${web.properties.defaultHostName}'
