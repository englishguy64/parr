// Web site (App Service). It only serves the page and tells it where the Backend API is.
// Deploy create_backendapi.bicep first, because it creates the App Service plan this site shares.

@description('Web site name. Globally unique (becomes <name>.azurewebsites.net).')
param webAppName string

@description('App Service plan created by create_backendapi.bicep.')
param appServicePlanName string

param location string = resourceGroup().location

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
      // Plain HTML and JavaScript: the Node image just serves the files. The Backend API address is written
      // into config.json by 06_deploy-webapp.ps1.
      linuxFxVersion: 'NODE|22-lts'
      appCommandLine: 'pm2 serve /home/site/wwwroot --no-daemon'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
    }
  }
}

output webUrl string = 'https://${web.properties.defaultHostName}'
