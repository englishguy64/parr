// The web site (App Service): a small ASP.NET app that serves the page and tells it where the Backend API is.
// Deploy create_backendapi.bicep first, it creates the App Service plan that the web site shares.
// Every value is a parameter and none has a default.

@description('Name of the web site. It becomes https://<name>.azurewebsites.net and must be unique in Azure.')
param webAppName string

@description('Name of the App Service plan created by create_backendapi.bicep.')
param planName string

@description('The address of the Backend API, for example https://<name>.azurewebsites.net. The page calls it directly.')
param backendApiUrl string

@description('Azure region.')
param location string

resource plan 'Microsoft.Web/serverfarms@2024-04-01' existing = {
  name: planName
}

resource web 'Microsoft.Web/sites@2024-04-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      http20Enabled: true
      alwaysOn: true
      appSettings: [
        { name: 'BACKEND_API_URL', value: backendApiUrl }
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'false' }
      ]
    }
  }
}

output webAppName string = web.name
output webAppUrl string = 'https://${web.properties.defaultHostName}/'
