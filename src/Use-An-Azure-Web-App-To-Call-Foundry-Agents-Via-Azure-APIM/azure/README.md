# Infrastructure - Azure Bicep Templates

**Note**: Foundry hosted agents can now also be deployed with the Foundry Toolkit for VS Code, from source code or from a container (preview). See [Hosted agents in Foundry Toolkit for VS Code](https://code.visualstudio.com/docs/intelligentapps/hosted-agents).

Infrastructure for the "Use an Azure Web App to Call Foundry Agents via Azure APIM" solution, in `src/Use-An-Azure-Web-App-To-Call-Foundry-Agents-Via-Azure-APIM/azure`. Every command below runs from that folder.

## Overview

A browser signs in with Microsoft Entra ID, calls Azure API Management (APIM), and APIM passes the call to a Backend API that talks to Microsoft Foundry agents. The scripts deploy:

- **Resource group** - `<TENANT_PREFIX>-rg1`, `germanywestcentral`
- **Virtual network** (`vnet-ai`, `10.0.0.0/16`) - four subnets, the NSG APIM needs, private DNS zones
- **Microsoft Foundry** - account, project, `gpt-4.1-mini` deployment, private endpoint
- **Prompt agents** (2) - Support and Research, created through the Agent Service REST API
- **Hosted agents** (3) - Orchestrator, Order Lookup, Policy Check, run from container images
- **Container Registry** (Basic) - holds the three hosted agent images
- **Backend API** (App Service) - reached only through APIM, calls Foundry with its managed identity
- **Storage account** - sample receipt that Order Lookup reads with Document Intelligence
- **Entra app registration** - one registration for the SPA sign-in and the API scope `access_as_user`
- **API Management** (Developer tier) - CORS, Entra token check, per-user rate limit
- **Website** (App Service) - static page that signs in with MSAL.js and calls APIM

## Architecture

```text
Browser (MSAL.js, Entra sign-in)
  │
  ▼
API Management (public gateway, apim-policy.xml)
  │  CORS · Entra token check · rate limit per user
  ▼
Backend API (App Service, snet-api)          Website (App Service)
  │  managed identity, no keys                 serves the page only
  ▼
Foundry project (private endpoint)
  ├── Prompt agents ── Support, Research
  └── Hosted agents ── Orchestrator ──┬── Order Lookup ── Document Intelligence ── Blob (receipt)
                                      └── Policy Check

vnet-ai (10.0.0.0/16)
  ├── snet-apim   API Management (external VNet mode)
  ├── snet-api    Backend API
  └── private DNS zones (Foundry x3, APIM)
```

## Files

| File | Purpose |
|------|---------|
| `01_create-resourcegroup.ps1` / `create_resourcegroup.bicep` | Resource group (subscription scope) |
| `02_create-network.ps1` / `create_network.bicep` | VNet, subnets, NSG, private DNS zones |
| `03_create-foundry.ps1` / `create_foundry.bicep` | Foundry account, project, model, private endpoint. `-LockDown` disables public access |
| `04_create-foundrypromptagents.ps1` / `create_foundrypromptagents.bicep` | Prompt agents, created by a deploymentScript |
| `05_create-acr.ps1` / `create_acr.bicep` | Container registry, Entra ID only, pull role for the Foundry project |
| `06_create-foundryhostedagents.ps1` / `create_foundryhostedagents.bicep` | Hosted agents from the registry images (preview REST API) |
| `07_create-backendapi.ps1` / `create_backendapi.bicep` | Backend API, shared App Service plan, storage account |
| `08_upload-samplereceipt.ps1` / `create_samplereceipt.bicep` | Sample receipt upload and read access |
| `09_deploy-backendapi.ps1` | Deploys the Backend API code |
| `10_create-entraapp.ps1` / `create_entraapp.bicep` | Entra app registration (Microsoft Graph Bicep extension) |
| `11_create-azureapim.ps1` / `create_azureapim.bicep` | API Management and its API, operations and policy |
| `12_create-webapp.ps1` / `create_webapp.bicep` | Website App Service |
| `13_deploy-website.ps1` | Deploys the website code |
| `15_create-hostedagentroles.ps1` / `create_hostedagentroles.bicep` | Roles Order Lookup needs for Document Intelligence and Blob |
| `postdeployment-securityfixes.ps1` / `.bicep` | Optional hardening of both App Services |
| `apim-policy.xml` | APIM policy: CORS, token validation, rate limit |
| `bicepconfig.json` | Bicep configuration (Microsoft Graph extension) |

## Key Features

- **Entra ID only**: Foundry has `disableLocalAuth: true`, the registry has no admin user, and the web app holds no secret
- **No keys in code**: every service call uses a managed identity
- **Private path to Foundry**: Backend API reaches Foundry through the private endpoint
- **Per-user rate limit**: APIM limits each user (default 60 calls a minute)
- **Prefix naming**: every resource name is built from `TENANT_PREFIX`
- **Re-runnable scripts**: deploymentScripts use `forceUpdateTag` so a re-run executes again

## Deployment

### Prerequisites

- Azure subscription where you are Owner (or Contributor plus User Access Administrator)
- Permission to register apps in Microsoft Entra ID
- Latest Azure CLI (`az upgrade`), signed in with `az login`
- Model quota for `gpt-4.1-mini` in `germanywestcentral`
- .NET 10 SDK, only to build or run the C# projects locally

### Run the scripts (recommended)

```powershell
$env:TENANT_PREFIX = 'myprefix64'          # unique prefix, many names must be globally unique
az login
az account set --subscription "<name or id>"

.\01_create-resourcegroup.ps1
.\02_create-network.ps1
.\03_create-foundry.ps1
.\04_create-foundrypromptagents.ps1
.\05_create-acr.ps1
```

Build the hosted agent images (no local Docker needed). The registry name is the prefix without symbols, lower case, plus `acr`:

```powershell
az acr build -r <registry name> -t orchestrator:latest ..\hostedagents\orchestrator
az acr build -r <registry name> -t order-lookup:latest ..\hostedagents\order-lookup
az acr build -r <registry name> -t policy-check:latest ..\hostedagents\policy-check
```

Continue:

```powershell
.\06_create-foundryhostedagents.ps1
.\07_create-backendapi.ps1
.\08_upload-samplereceipt.ps1
.\09_deploy-backendapi.ps1
.\15_create-hostedagentroles.ps1           # Order Lookup roles
.\10_create-entraapp.ps1
.\11_create-azureapim.ps1 -PublisherEmail you@example.com   # 30-60+ minutes
.\12_create-webapp.ps1
.\13_deploy-website.ps1
.\postdeployment-securityfixes.ps1         # optional hardening
.\03_create-foundry.ps1 -LockDown          # last: private endpoint only
```

### Direct Bicep (advanced)

```powershell
az deployment group create -g <resource-group> `
  -f create_foundry.bicep `
  -p foundryName=<name> projectName=<project>
```

`01_create-resourcegroup` deploys at subscription scope (`az deployment sub create`). The scripts also pass the outputs of earlier steps between templates.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TENANT_PREFIX` (env var) | (required) | Prefix for every resource name |
| `location` | `germanywestcentral` | Region for all resources |
| `vnetName` | `vnet-ai` | Virtual network name |
| `foundryName` / `projectName` | (required) | Foundry account and project names |
| `publicNetworkAccess` | `Enabled` | Foundry public access. `-LockDown` sets `Disabled` |
| `modelName` / `modelVersion` | `gpt-4.1-mini` / `2025-04-14` | Chat model |
| `modelDeploymentName` | `gpt-4.1-mini` | Deployment name the agents use |
| `modelCapacity` | `50` | GlobalStandard capacity for the model |
| `sku` (registry) | `Basic` | Container Registry SKU |
| `PlanSku` (`07` script) | `B1` | App Service plan SKU, passed to the template as `appServiceSku`. One plan serves the Backend API and the website |
| `publisherEmail` / `publisherName` | (required) | APIM publisher details |
| `allowedOrigins` | (required) | Origins APIM accepts for CORS |
| `rateLimitPerMinute` | `60` | Calls per user per minute through APIM |
| `includeLocalhost` | `true` | Adds localhost redirect URIs. `-NoLocalhost` turns it off |
| `forceUpdateTag` | `utcNow()` | Forces deploymentScripts to run again |

## Outputs

| Output | Purpose |
|--------|---------|
| `resourceGroupName` | Name of the created resource group |
| `vnetName` | Network name passed to later templates |
| `projectEndpoint` | Foundry project endpoint for the Backend API |
| `modelDeployment` | Model deployment name |
| `agentNames` | Names of the prompt agents |
| `hostedAgentNames` | Names of the hosted agents |
| `loginServer` | Container registry address for image builds |
| `storageAccountName` / `appServicePlanName` | Passed to the receipt and web app templates |
| `backendUrl` | Backend API address that APIM calls |
| `sampleReceiptUrl` | Blob address of the sample receipt |
| `clientId` / `redirectUris` | Entra app values for the website and APIM |
| `gatewayUrl` / `apiBaseUrl` | APIM address the browser calls |
| `webAppUrl` | Website address |

## Resource Configuration

### Foundry

- **Account**: SKU `S0`, Entra ID only, custom subdomain
- **Model**: `GlobalStandard`, capacity from `modelCapacity`
- **Network**: private endpoint with three DNS zones (`privatelink.services.ai`, `.cognitiveservices`, `.openai`)

### Hosted agents

- **Source**: container images from the registry, `1` CPU and `2Gi` memory each
- **Protocol**: `responses`, port `8088`
- **Created by**: a deploymentScript that calls the Agent Service REST API (`2025-11-15-preview`)
- **Identity**: each agent has its own agent identity. Roles go on that identity, not on your user

### API Management

- **Tier**: Developer, one unit, external VNet mode in `snet-apim`
- **Public IP**: Standard static, required by the Developer tier in a VNet
- **Policy**: `apim-policy.xml`

### App Service

- **Plan**: one plan shared by the Backend API and the website
- **Backend API**: VNet-integrated in `snet-api`, reachable only through APIM

## Security

- ✅ Foundry, storage and the registry accept Entra ID only (no keys, no admin user, no anonymous pull)
- ✅ The website holds no secret. The SPA uses authorization code flow with PKCE
- ✅ APIM accepts only tokens issued for the app and the `access_as_user` scope
- ✅ The Backend API accepts calls through APIM only
- ✅ Optional hardening: TLS 1.2, FTP off, publishing password off, remote debugging off
- ⚠️ Foundry public access stays `Enabled` until you run `03_create-foundry.ps1 -LockDown`
- ⚠️ The registry and storage account have public endpoints, protected by Entra ID

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Please run 'az login'` or unknown arguments | Run `az login` again, or `az upgrade` |
| Name already taken | Use a different `TENANT_PREFIX` |
| `AuthorizationFailed` on a role | You need Owner or User Access Administrator |
| `InsufficientQuota` or SKU not available | Request quota, lower `modelCapacity`, or change region |
| 401 or 403 right after a deployment | A new role is still taking effect. Wait a few minutes |
| Agent scripts fail after `-LockDown` | Redeploy without `-LockDown`, run the agent scripts, then lock down again |
| Hosted agent call fails | Check the image exists in the registry and the agent shows an active version |
| Receipt returns a 500 | Run `15_create-hostedagentroles.ps1`, then wait up to 10 minutes |
| Sign-in fails | A red banner under the header shows the reason. Check the redirect URI in the Entra app |

## Customization

### Change model capacity or region

Edit `create_foundry.bicep`:

```bicep
param modelCapacity int = 50              // lower if quota is short
param location string = 'germanywestcentral'  // change region
```

### Change the App Service tier

Pass `-PlanSku` to the script (default `B1`):

```powershell
.\07_create-backendapi.ps1 -PlanSku B1
```

The script passes it to `create_backendapi.bicep` as `appServiceSku`. If you deploy that template directly, pass `appServiceSku=B1` yourself.

### Change the APIM rate limit

Edit `create_azureapim.bicep`:

```bicep
param rateLimitPerMinute int = 60         // calls per user per minute
```

### Add or change a hosted agent

Edit the `hostedAgents` map in `create_foundryhostedagents.bicep`: agent name to image (`repository:tag`). Build the image first with `az acr build`.

## Validation

```powershell
# Test Bicep syntax
az bicep build --file create_foundry.bicep

# What-if deployment
az deployment group what-if -g $env:TENANT_PREFIX-rg1 `
  -f create_foundry.bicep `
  -p foundryName=$env:TENANT_PREFIX projectName="$env:TENANT_PREFIX-FoundryProject"
```

For a walkthrough of the solution itself, see `src/Use-An-Azure-Web-App-To-Call-Foundry-Agents-Via-Azure-APIM/README.md`.
