// Virtual network vnet-ai (10.0.0.0/16) with the four subnets from the diagram,
// the NSG API Management needs, and the private DNS zones used by the private endpoint and APIM.
// Deploy after create_resourcegroup.bicep.

param vnetName string = 'vnet-ai'
param location string = 'germanywestcentral'

// Private DNS zones: Foundry private endpoint (three zones), and the internal APIM gateway.
var dnsZones = [
  'privatelink.services.ai.azure.com'
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'azure-api.net'
]

// API Management (stv2, external VNet mode) requires these rules on its subnet. The gateway is public: browsers call
// it on 443, and the policies in apim-policy.xml check the caller's Entra token.
resource apimNsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-snet-apim'
  location: location
  properties: {
    securityRules: [
      { name: 'in-apim-management', properties: { priority: 100, direction: 'Inbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: 'ApiManagement', sourcePortRange: '*', destinationAddressPrefix: 'VirtualNetwork', destinationPortRange: '3443' } }
      { name: 'in-azure-load-balancer', properties: { priority: 110, direction: 'Inbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: 'AzureLoadBalancer', sourcePortRange: '*', destinationAddressPrefix: 'VirtualNetwork', destinationPortRange: '6390' } }
      { name: 'in-https-from-vnet', properties: { priority: 120, direction: 'Inbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: 'VirtualNetwork', sourcePortRange: '*', destinationAddressPrefix: 'VirtualNetwork', destinationPortRange: '443' } }
      { name: 'in-https-from-internet', properties: { priority: 130, direction: 'Inbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: 'Internet', sourcePortRange: '*', destinationAddressPrefix: 'VirtualNetwork', destinationPortRange: '443' } }
      { name: 'out-storage', properties: { priority: 100, direction: 'Outbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: 'VirtualNetwork', sourcePortRange: '*', destinationAddressPrefix: 'Storage', destinationPortRange: '443' } }
      { name: 'out-sql', properties: { priority: 110, direction: 'Outbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: 'VirtualNetwork', sourcePortRange: '*', destinationAddressPrefix: 'Sql', destinationPortRange: '1433' } }
      { name: 'out-key-vault', properties: { priority: 120, direction: 'Outbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: 'VirtualNetwork', sourcePortRange: '*', destinationAddressPrefix: 'AzureKeyVault', destinationPortRange: '443' } }
      { name: 'out-entra-id', properties: { priority: 130, direction: 'Outbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: 'VirtualNetwork', sourcePortRange: '*', destinationAddressPrefix: 'AzureActiveDirectory', destinationPortRange: '443' } }
      { name: 'out-monitor', properties: { priority: 140, direction: 'Outbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: 'VirtualNetwork', sourcePortRange: '*', destinationAddressPrefix: 'AzureMonitor', destinationPortRanges: ['443', '1886'] } }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: ['10.0.0.0/16'] }
    subnets: [
      {
        // Web App regional VNet integration.
        name: 'snet-web'
        properties: {
          addressPrefix: '10.0.1.0/24'
          delegations: [
            { name: 'Microsoft.Web/serverFarms', properties: { serviceName: 'Microsoft.Web/serverFarms' } }
          ]
        }
      }
      {
        // API Management (Developer tier, internal VNet mode). Dedicated to APIM.
        name: 'snet-apim'
        properties: {
          addressPrefix: '10.0.2.0/24'
          networkSecurityGroup: { id: apimNsg.id }
          // Lets the Backend API restrict inbound traffic to this subnet.
          serviceEndpoints: [{ service: 'Microsoft.Web' }]
        }
      }
      {
        // Backend API (App Service) regional VNet integration, for its calls to Foundry.
        name: 'snet-api'
        properties: {
          addressPrefix: '10.0.4.0/24'
          delegations: [
            { name: 'Microsoft.Web/serverFarms', properties: { serviceName: 'Microsoft.Web/serverFarms' } }
          ]
        }
      }
      {
        // Private endpoint for Foundry.
        name: 'snet-pe'
        properties: { addressPrefix: '10.0.3.0/24' }
      }
    ]
  }
}

resource zones 'Microsoft.Network/privateDnsZones@2024-06-01' = [for z in dnsZones: {
  name: z
  location: 'global'
}]

resource zoneLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [for (z, i) in dnsZones: {
  parent: zones[i]
  name: '${vnetName}-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnet.id }
    registrationEnabled: false
  }
}]

output vnetName string = vnet.name
