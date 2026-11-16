// Creates the resource group that every other template deploys into. Deploy this first.
// This is a subscription-scope deployment (az deployment sub create), unlike the other templates.

targetScope = 'subscription'

param resourceGroupName string
param location string = 'germanywestcentral'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

output resourceGroupName string = rg.name
