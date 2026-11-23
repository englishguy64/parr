// Azure API Management (Developer tier) injected into snet-apim in external VNet mode: the gateway is public, so
// browsers call it directly, and it reaches the Backend API privately through the VNet.
// Browser -> APIM (apim-policy.xml: CORS, Entra token check, per-user rate limit) -> Backend API -> Foundry.
// Deploy create_network.bicep and create_backendapi.bicep first. Developer tier takes 30-60+ minutes to deploy.

@description('API Management service name. Must be globally unique.')
param apimName string

@description('Publisher email shown in the APIM portal and used for notifications.')
param publisherEmail string

@description('Publisher name shown in the APIM portal.')
param publisherName string

@description('Backend API web app name (created by create_backendapi.bicep).')
param backendName string

@description('Origins allowed to call the gateway from a browser (CORS), for example https://<web app>.azurewebsites.net.')
param allowedOrigins array

@description('Entra tenant that issues the access tokens APIM accepts.')
param entraTenantId string = tenant().tenantId

@description('Client id of the Entra app registration (create_entraapp.bicep). The access token audience must be this app.')
param apiClientId string

@description('Calls per minute allowed for each signed-in user.')
param rateLimitPerMinute int = 60

@description('Virtual network created by create_network.bicep.')
param vnetName string = 'vnet-ai'

param location string = 'germanywestcentral'

var backendUrl = 'https://${backendName}.azurewebsites.net'

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName
}

// Developer tier in a VNet (stv2) needs a Standard static public IP for the management plane.
resource pip 'Microsoft.Network/publicIPAddresses@2024-05-01' = {
  name: '${apimName}-pip'
  location: location
  sku: { name: 'Standard' }
  properties: {
    publicIPAllocationMethod: 'Static'
    dnsSettings: { domainNameLabel: toLower(apimName) }
  }
}

resource apim 'Microsoft.ApiManagement/service@2024-05-01' = {
  name: apimName
  location: location
  sku: { name: 'Developer', capacity: 1 }
  identity: { type: 'SystemAssigned' }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    virtualNetworkType: 'External'
    virtualNetworkConfiguration: { subnetResourceId: '${vnet.id}/subnets/snet-apim' }
    publicIpAddressId: pip.id
  }
}

resource api 'Microsoft.ApiManagement/service/apis@2024-05-01' = {
  parent: apim
  name: 'backend'
  properties: {
    displayName: 'Backend API'
    path: 'api'
    protocols: ['https']
    serviceUrl: backendUrl
    subscriptionRequired: false // callers are identified by their Entra token (apim-policy.xml), not a shared key
  }
}

// Pass-through operations: /api/* is forwarded to the Backend API.
var methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
resource operations 'Microsoft.ApiManagement/service/apis/operations@2024-05-01' = [for m in methods: {
  parent: api
  name: toLower(m)
  properties: {
    displayName: m
    method: m
    urlTemplate: '/*'
  }
}]

// Policies live in apim-policy.xml: CORS, Entra token validation, per-user rate limit, caller headers.
var originsXml = join(map(allowedOrigins, o => '<origin>${o}</origin>'), '')
var policyXml = replace(replace(replace(replace(loadTextContent('apim-policy.xml'), '{{ORIGINS}}', originsXml), '{{TENANT}}', entraTenantId), '{{CLIENT_ID}}', apiClientId), '{{RATE_CALLS}}', string(rateLimitPerMinute))

resource apiPolicy 'Microsoft.ApiManagement/service/apis/policies@2024-05-01' = {
  parent: api
  name: 'policy'
  properties: {
    format: 'xml'
    value: policyXml
  }
  dependsOn: [operations]
}

output gatewayUrl string = apim.properties.gatewayUrl
output apiBaseUrl string = '${apim.properties.gatewayUrl}/api'
