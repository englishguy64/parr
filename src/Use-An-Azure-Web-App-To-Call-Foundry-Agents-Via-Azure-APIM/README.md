# Use an Azure Web App to Call Foundry Agents via Azure APIM

**Note**: Foundry hosted agents can now also be deployed with the Foundry Toolkit for VS Code, from source code or from a container (preview). See [Hosted agents in Foundry Toolkit for VS Code](https://code.visualstudio.com/docs/intelligentapps/hosted-agents).

A web page signs the user in with Microsoft Entra ID and calls Azure API Management (APIM). APIM checks the user's token and passes the call to a Backend API, which calls the Microsoft Foundry agents. This README explains how the pieces work together. For the infrastructure scripts and templates, see [azure/README.md](azure/README.md).

## Overview

- **Website** (App Service) - one page with a chat box and an agent picker. Signs in with MSAL.js, calls APIM directly
- **API Management** - public gateway. Answers CORS, checks the Entra token, limits each user
- **Backend API** (App Service, ASP.NET, .NET 10) - maps a public agent name to a Foundry agent and calls it with its managed identity
- **Prompt agents** (2) - instructions only, no code. Called `support` and `research` on the page
- **Hosted agents** (3) - your own C# code running in Foundry: Orchestrator, Order Lookup, Policy Check
- **Document Intelligence** - Order Lookup uses it to read a receipt
- **Blob Storage** - holds the sample receipt, readable with Entra ID only

## Architecture

```text
Browser
  │ 1. Sign in with Entra (MSAL.js), get a token for api://<client id>/access_as_user
  │ 2. POST /chat  (agent, message)  + Bearer token
  ▼
API Management ── CORS · validate token · 60 calls a minute per user
  │ 3. forwards the call, adds x-user-oid, removes the token
  ▼
Backend API ── managed identity
  │ 4. picks the Foundry agent from the public name
  ▼
Foundry project
  ├── support   → <prefix>-agentone   (prompt agent)
  ├── research  → <prefix>-agenttwo   (prompt agent)
  ├── order-lookup → Order Lookup ── Document Intelligence ── Blob (receipt)
  └── orchestrator → Orchestrator ──┬── Order Lookup
                                    └── Policy Check

Browser ── 5. GET /chat/{jobId} until status is done or failed
```

## Folders

| Folder | Purpose |
|--------|---------|
| `azure` | Scripts and Bicep templates. See [azure/README.md](azure/README.md) |
| `website` | The web page (`wwwroot`) and a small ASP.NET server that serves it and `/config.json` |
| `backendapi` | The Backend API |
| `hostedagents/orchestrator` | Plans, delegates and combines |
| `hostedagents/order-lookup` | Order data and receipt reading |
| `hostedagents/policy-check` | Return and refund rules |

## Key Features

- **No secrets in the browser**: the page uses authorization code flow with PKCE
- **Token stays at the gateway**: APIM validates the user's token, then removes it before the Backend API
- **Per-user limits**: APIM counts calls by the user's `oid`, not by IP address
- **No long-held requests**: the browser polls for slow answers
- **No server state**: the job id is Foundry's response id, so the Backend API can restart or scale out
- **Same answer every time for rules**: Policy Check is plain C#, not a prompt

## Walkthrough

One message, from the browser to the answer. The numbers match the architecture above.

### 1. Sign in

`website/wwwroot/app.js` loads `/config.json` (APIM address, tenant id, client id). None are secrets. It then starts MSAL.js with the Entra app registration and asks for the scope `api://<client id>/access_as_user`. Tokens are cached in `sessionStorage`. If sign-in fails, a red banner under the header explains why (missing consent, redirect URI not registered, account not allowed).

With no `ENTRA_CLIENT_ID` the Login button is hidden. That is the local mode.

### 2. Send a message

The page posts a form to `{APIM}/chat` with two fields, `agent` (`support`, `research`, `orchestrator` or `order-lookup`) and `message`, and the access token as a Bearer header.

### 3. API Management checks the call

`azure/apim-policy.xml` runs these steps in order:

1. **CORS** first, so the browser's preflight (which has no token) is answered
2. **validate-jwt**: the token must come from your tenant, be for this app, and carry the `access_as_user` scope. Otherwise `401`
3. **rate-limit-by-key**: 60 calls a minute per user (`oid` claim)
4. **Headers**: sets `x-user-oid` and `x-user-tenant`, then deletes `Authorization`. The Backend API never sees the user's token

### 4. The Backend API calls Foundry

`backendapi/Program.cs` maps the public name to a Foundry agent using app settings:

| Public name | App setting | Foundry agent | Kind |
|-------------|-------------|---------------|------|
| `support` | `AGENT_SUPPORT` | `<prefix>-agentone` | Prompt agent |
| `research` | `AGENT_RESEARCH` | `<prefix>-agenttwo` | Prompt agent |
| `orchestrator` | `AGENT_ORCHESTRATOR` | `<prefix>-orchestrator` | Hosted agent |
| `order-lookup` | `AGENT_ORDER_LOOKUP` | `<prefix>-order-lookup` | Hosted agent |

It gets a token for Foundry with its own managed identity and then:

- **Prompt agents**: posts to the project's `/openai/v1/responses` with an `agent_reference`, `background: true` and `store: true`. Foundry answers at once with a response id. The Backend API returns `202 {"jobId": ...}`
- **Hosted agents**: posts to the agent's own endpoint, `/agents/<name>/endpoint/protocols/openai/responses`. These answer in the same request, so the reply comes back as `200`

If the message mentions a receipt and goes to Order Lookup or the Orchestrator, the Backend API appends the sample receipt's blob address. It never reads the file itself.

### 5. The agents

**Prompt agents** are created from instructions only:

- `agentone`: "a concise, friendly English assistant. Answer in at most three sentences."
- `agenttwo`: "an English tutor. Correct the user's grammar and briefly explain why."

**Order Lookup** (`hostedagents/order-lookup`):

- A message with an `https` link: reads it as a receipt with Document Intelligence (`prebuilt-receipt`) and returns merchant, date, total and items. A blob link is downloaded with the agent's own identity first, because the service can't open private storage
- A message with an order id: looks it up in a built-in list (stand-in for a real order system)

| Order | Status | Date | Total | Item |
|-------|--------|------|-------|------|
| `ORD-1001` | Delivered | 2026-11-02 | 49.90 | Running shoes |
| `ORD-1002` | Shipped | 2026-11-14 | 129.00 | Backpack |
| `ORD-1003` | Processing | 2026-11-17 | 19.50 | Water bottle |

**Policy Check** (`hostedagents/policy-check`) decides `approved`, `manual_review`, `denied` or `needs_more_info`:

1. The order must be delivered
2. Returns are accepted within 30 days of the order date
3. Gift cards, perishable and personalised items can't be returned
4. Refunds over 100 need a person to review them

**Orchestrator** (`hostedagents/orchestrator`) works in three steps:

1. **Plan**: asks the model which agents are needed, as JSON (`{"steps":[{"agent","input"}]}`). If the plan is unusable, it asks every agent the original question
2. **Delegate**: calls the chosen agents in parallel. If the message holds an attachment link, it makes sure the link reaches Order Lookup unchanged
3. **Combine**: asks the model to write one short reply from the agents' results. A failed agent is reported as not checked

### 6. Polling for the answer

For a `202`, the browser calls `GET {APIM}/chat/{jobId}` until the status is `done` or `failed`:

- Delays grow from 1 s by 0.5 s a try, up to 5 s
- Gives up after 10 minutes (the job may still finish) or 5 failed polls in a row
- The job id is kept in `sessionStorage`, so a page refresh resumes the wait
- The Backend API does one lookup per poll and keeps no state

### Example: "Can I return ORD-1001?"

1. You pick **Orchestrator** and send the message
2. The Orchestrator plans: Order Lookup for `ORD-1001`, then Policy Check
3. Order Lookup returns the order JSON. Policy Check judges it: delivered, within 30 days, under 100 gives `approved`
4. The Orchestrator writes a short reply

The date rule counts from today, so the sample orders age out. After 30 days from `2026-11-02`, `ORD-1001` is denied. `ORD-1002` (Shipped) is denied as not delivered. `ORD-1003` is denied as not delivered too.

### Example: the receipt

Send "Read my receipt" to **Order Lookup**. The Backend API adds the sample receipt's blob address. Order Lookup downloads it with its own identity, Document Intelligence reads it, and you get the merchant, date, total and items.

## Deployment

You need an Azure subscription where you are Owner (or Contributor plus User Access Administrator), permission to register apps in Entra ID, the latest Azure CLI, and model quota for `gpt-4.1-mini` in `germanywestcentral`. The .NET 10 SDK is only for building locally.

```powershell
$env:TENANT_PREFIX = 'myprefix64'      # unique prefix, many names must be globally unique
az login
az account set --subscription "<name or id>"
cd azure
```

Run the scripts in the `azure` folder in this order:

| Script | What it does |
|--------|--------------|
| `01_create-resourcegroup.ps1` | Creates the resource group |
| `02_create-network.ps1` | Creates the virtual network and private DNS |
| `03_create-foundry.ps1` | Creates Foundry, the project, the model and the private endpoint |
| `04_create-foundrypromptagents.ps1` | Creates the two prompt agents |
| `05_create-acr.ps1` | Creates the container registry (then build the images) |
| `06_create-foundryhostedagents.ps1` | Creates the three hosted agents |
| `07_create-backendapi.ps1` | Creates the Backend API and the storage account |
| `08_upload-samplereceipt.ps1` | Uploads the sample receipt |
| `09_deploy-backendapi.ps1` | Deploys the Backend API code |
| `15_create-hostedagentroles.ps1` | Gives Order Lookup the roles it needs |
| `10_create-entraapp.ps1` | Registers the sign-in app in Entra ID |
| `11_create-azureapim.ps1 -PublisherEmail you@example.com` | Creates API Management (30 to 60 minutes or more) |
| `12_create-webapp.ps1` | Creates the web app |
| `13_deploy-website.ps1` | Deploys the website code |
| `postdeployment-securityfixes.ps1` | Optional hardening |

Build the hosted agent images after `05_create-acr.ps1`. No local Docker is needed:

```powershell
az acr build -r <registry name> -t orchestrator:latest ..\hostedagents\orchestrator
az acr build -r <registry name> -t order-lookup:latest ..\hostedagents\order-lookup
az acr build -r <registry name> -t policy-check:latest ..\hostedagents\policy-check
```

When everything works, run `03_create-foundry.ps1 -LockDown` to make Foundry reachable only through its private endpoint. Do this last, because the agent scripts need public access. For all parameters, outputs and options, see [azure/README.md](azure/README.md).

## Configuration

| Component | Setting | Purpose |
|-----------|---------|---------|
| Website | `APIM_BASE_URL` | APIM address, for example `https://<prefix>-apim.azure-api.net/api`. Empty runs a local stand-in |
| Website | `ENTRA_TENANT_ID` / `ENTRA_CLIENT_ID` | Entra tenant and app. Empty client id turns sign-in off |
| Backend API | `FOUNDRY_PROJECT_ENDPOINT` | Foundry project address |
| Backend API | `AGENT_SUPPORT` / `AGENT_RESEARCH` / `AGENT_ORCHESTRATOR` / `AGENT_ORDER_LOOKUP` | Foundry agent behind each public name |
| Backend API | `SAMPLE_RECEIPT_URL` | Blob address added to receipt messages |
| Orchestrator | `FOUNDRY_PROJECT_ENDPOINT` | Foundry project address |
| Orchestrator | `FOUNDRY_MODEL_DEPLOYMENT` | Model for planning and the final reply (default `gpt-4.1-mini`) |
| Orchestrator | `CUSTOM_AGENTS` | Agents it may delegate to, set by the Bicep |
| Order Lookup | `DOCUMENT_INTELLIGENCE_ENDPOINT` | Foundry resource address |
| Order Lookup | `STORAGE_ACCOUNT` | Only this account's blobs are downloaded (empty allows any blob address) |

None of these is a secret.

## Try it

Sign in on the website, pick an agent and chat. To test the receipt demo, send a message containing the word "receipt" to Order Lookup or the Orchestrator.

To run the pieces on your PC:

- **Website**: run `dotnet run` in `website`. With no `APIM_BASE_URL` it only echoes your messages
- **Backend API**: set `FOUNDRY_PROJECT_ENDPOINT` and the `AGENT_*` variables, run `az login`, then `dotnet run` in `backendapi`. Your user needs the Azure AI User role, and Foundry must allow public access
- **Policy Check**: `dotnet run -- "{\"Id\":\"ORD-1001\",\"Status\":\"Delivered\",\"OrderDate\":\"2026-11-02\",\"Total\":49.90,\"Item\":\"Running shoes\"}"` prints a decision
- **Order Lookup**: set `DOCUMENT_INTELLIGENCE_ENDPOINT`, then `dotnet run -- sample-receipt.png` reads the receipt in that folder

## Security

- ✅ Foundry, storage and the registry accept Entra ID only
- ✅ The website has no secret, and the user's token never reaches the Backend API
- ✅ APIM accepts only tokens issued for the app and the `access_as_user` scope
- ✅ The Backend API calls Foundry with its managed identity
- ⚠️ Foundry public access stays on until you run `03_create-foundry.ps1 -LockDown`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Please run 'az login'` or unknown arguments | Run `az login` again, or `az upgrade` |
| Name already taken | Use a different `TENANT_PREFIX` |
| `AuthorizationFailed` on a role | You need Owner or User Access Administrator |
| `InsufficientQuota` or SKU not available | Request quota, lower `modelCapacity`, or change region |
| 401 or 403 right after a deployment | A new role is still taking effect. Wait a few minutes |
| 401 from APIM | The token is missing, expired, or for a different app or scope. Sign in again |
| 429 from APIM | More than 60 calls a minute for your user. Wait a minute |
| 502 from the Backend API | Foundry call failed. The `detail` field in the response shows why |
| 500 "not configured" | `FOUNDRY_PROJECT_ENDPOINT` or an `AGENT_*` setting is missing on the Backend API |
| Agent scripts fail after `-LockDown` | Redeploy without `-LockDown`, run the agent scripts, then lock down again |
| Receipt returns a 500 | Run `15_create-hostedagentroles.ps1`, then wait up to 10 minutes |
| Sign-in fails | A red banner under the header shows the reason. Check the redirect URI in the Entra app |

## Customization

### Change the return rules

Edit the constants at the top of `hostedagents/policy-check/Program.cs`:

```csharp
const int ReturnWindowDays = 30;
const decimal ManualReviewOver = 100m;
```

### Replace the order data

Order Lookup keeps its orders in the `orders` dictionary in `hostedagents/order-lookup/Program.cs`. Replace it with a call to your order API or database.

### Change the prompt agents

Edit the `agents` map in `azure/create_foundrypromptagents.bicep` (agent name to instructions), then run `04_create-foundrypromptagents.ps1` again.

### Add a hosted agent

1. Create a folder in `hostedagents` with an app that listens on port `8088` and answers `POST /responses`
2. Add its image to the `hostedAgents` map in `azure/create_foundryhostedagents.bicep` and build the image with `az acr build`
3. To call it from the Backend API, add an `AGENT_*` setting in `azure/create_backendapi.bicep`, add it to the `agents` map in `backendapi/Program.cs`, and add it to the `hosted` check there (hosted agents use their own endpoint)
4. Add an option in `website/wwwroot/index.html`

## Validation

```powershell
dotnet build backendapi
dotnet build website
dotnet build hostedagents/orchestrator
dotnet build hostedagents/order-lookup
dotnet build hostedagents/policy-check
```

For the infrastructure templates, see the Validation section in [azure/README.md](azure/README.md).
