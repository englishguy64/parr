# Use an Azure Web App to Call Foundry Agents via Azure APIM

A web page signs the user in with Microsoft Entra ID and calls Azure API Management (APIM). APIM checks the user's token and passes the call to a Backend API, which calls the Microsoft Foundry agents.

## Before you start

- An Azure subscription where you are Owner (or Contributor plus User Access Administrator).
- Permission to register apps in Microsoft Entra ID.
- The latest Azure CLI. Run `az upgrade`, then sign in with `az login` and pick your subscription with `az account set --subscription "<name or id>"`.
- Model quota for `gpt-4.1-mini` in `germanywestcentral`. If you don't have it, lower `modelCapacity` in `azure/create_foundry.bicep` or choose another region.
- The .NET 10 SDK, only if you build or run the C# projects on your PC.

## How to use it

Set a prefix that nobody else is likely to use. Every resource name is built from it, and many names must be globally unique.

```powershell
$env:TENANT_PREFIX = 'myprefix64'
```

Then run the scripts in the `azure` folder, in this order.

| Script | What it does |
| --- | --- |
| `01_create-resourcegroup.ps1` | Creates the resource group |
| `02_create-network.ps1` | Creates the virtual network and private DNS |
| `03_create-foundry.ps1` | Creates Foundry, the project, the model and the private endpoint |
| `04_create-foundrypromptagents.ps1` | Creates the Support and Research agents |
| `05_create-acr.ps1` | Creates the container registry (then build the images, see below) |
| `06_create-foundryhostedagents.ps1` | Creates the Orchestrator, Order Lookup and Policy Check agents |
| `07_create-backendapi.ps1` | Creates the Backend API and the storage account |
| `08_upload-samplereceipt.ps1` | Uploads the sample receipt and gives you read access to it |
| `09_deploy-backendapi.ps1` | Deploys the Backend API code |
| `15_create-hostedagentroles.ps1` | Gives Order Lookup the roles it needs to read receipts |
| `10_create-entraapp.ps1` | Registers the sign-in app in Entra ID |
| `11_create-azureapim.ps1 -PublisherEmail you@example.com` | Creates API Management (takes 30 to 60 minutes or more) |
| `12_create-webapp.ps1` | Creates the web app |
| `13_deploy-website.ps1` | Deploys the website code |
| `postdeployment-securityfixes.ps1` | Optional hardening: TLS 1.2, no FTP, no publishing password |

Build the Hosted Agent images after `05_create-acr.ps1`. No local Docker is needed. The registry name is your prefix without symbols, in lower case, plus `acr`.

```powershell
az acr build -r <registry name> -t orchestrator:latest .\hostedagents\orchestrator
az acr build -r <registry name> -t order-lookup:latest .\hostedagents\order-lookup
az acr build -r <registry name> -t policy-check:latest .\hostedagents\policy-check
```

When everything works, you can run `03_create-foundry.ps1 -LockDown` to make Foundry reachable only through its private endpoint. Do this last, because the agent scripts need public access.

To keep localhost sign-in off, add `-NoLocalhost` when you run `10_create-entraapp.ps1` and `11_create-azureapim.ps1`.

## What is in each folder

- `azure` holds the scripts and the Bicep templates they deploy.
- `website` holds the web page, which signs in with MSAL.js and calls APIM.
- `backendapi` holds the Backend API (ASP.NET, .NET 10).
- `hostedagents` holds the source for the Orchestrator, Order Lookup and Policy Check containers.

## Try it

Sign in on the website and chat with an agent. To test the receipt demo, send a message containing the word "receipt" to Order Lookup or the Orchestrator.

To run the pieces on your PC instead:

- Website: run `dotnet run` in the `website` folder. With no `APIM_BASE_URL` set it only echoes your messages.
- Backend API: set `FOUNDRY_PROJECT_ENDPOINT` and the `AGENT_*` variables, run `az login`, then run `dotnet run` in the `backendapi` folder. Your user needs the Azure AI User role.

## Good to know

- Hosted Agents are a Foundry preview feature, so their calls may change.
- Every new version of a Hosted Agent gets a new identity. After creating a new Order Lookup version, run `15_create-hostedagentroles.ps1` again.
- There are no keys anywhere. Foundry, storage and the registry accept Entra ID only, and the web app has no secret.

## Cost

Roughly: APIM Developer about $48 a month, the App Service plan $13 (B1) to $60 (P0v3), and Container Registry about $5. The Foundry model and agents are pay per use. Delete the resource group when you are done.

## If something goes wrong

| Problem | What to do |
| --- | --- |
| `Please run 'az login'` or unknown arguments | Run `az login` again, or `az upgrade` |
| Name already taken | Use a different `TENANT_PREFIX` |
| `AuthorizationFailed` on a role | You need Owner or User Access Administrator |
| `InsufficientQuota` or SKU not available | Request quota, lower `modelCapacity`, or change region |
| 401 or 403 right after a deployment | The new role is still taking effect. Wait a few minutes |
| Agent scripts fail after `-LockDown` | Redeploy without `-LockDown`, run the agent scripts, then lock down again |
| Receipt returns a 500 | Run `15_create-hostedagentroles.ps1`, then wait up to 10 minutes |
| Sign-in fails | A red banner under the header shows the reason. Check the redirect URI in the Entra app |
