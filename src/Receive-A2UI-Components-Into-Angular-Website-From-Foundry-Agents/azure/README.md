# Azure scripts

Bicep templates and PowerShell scripts that deploy the two hosted agents, `a2ui-response` and `a2ui-stream`, **from source**. No container and no registry. They use the existing Foundry resource and project, and create only the agents and the role assignments they need.

They are adapted from the scripts in the [Using AG-UI Protocol With Foundry Agents](../../Using-AG-UI-Protocol-With-Foundry-Agents/azure/README.md) recipe. The one difference is that the two agents are registered with **different protocols**:

| Agent | Registered protocol | Why |
|-------|---------------------|-----|
| `a2ui-response` | `responses` 2.0.0 | Returns its data via the Responses protocol |
| `a2ui-stream` | `invocations` 2.0.0 | Foundry has no AG-UI protocol. The Invocations protocol passes any request through, so the agent can serve AG-UI and stream raw Server-Sent Events |

| File | Purpose |
|------|---------|
| `01_deploy-hostedagents.ps1` | Zips each agent folder and runs `create_hostedagents.bicep` |
| `create_hostedagents.bicep` | Uploads the zips to Foundry, registers each agent with its protocol, and waits until each agent is active |
| `02_create-hostedagentroles.ps1` | Reads the agents' identities and runs `create_hostedagentroles.bicep` |
| `create_hostedagentroles.bicep` | Gives each agent the Azure AI User role on the Foundry resource |

## Before you run

- The Azure CLI, signed in with `az login`, on the subscription that holds Foundry
- An existing Foundry resource and project, and a chat model deployment (default `gpt-4.1-mini`)
- Owner, or Contributor plus User Access Administrator, on the resource group (the scripts create role assignments)
- Foundry public access still on, because the deployment calls its data-plane API
- No local .NET SDK is needed: Foundry builds the code

Set the prefix, and the resource group, Foundry resource and project names follow from it (the same convention as the other recipes):

```powershell
$env:TENANT_PREFIX = 'your-tenant-prefix'     # Foundry resource: <prefix>, project: <prefix>-FoundryProject, group: <prefix>-rg1
az login
az account set --subscription "<name or id>"
cd src\Receive-A2UI-Components-Into-Angular-Website-From-Foundry-Agents\azure
```

Each script also takes parameters (`-ResourceGroup`, `-FoundryName`, `-ProjectName`) if your names differ. `01` also takes `-ModelDeployment`.

## Run

```powershell
.\01_deploy-hostedagents.ps1
.\02_create-hostedagentroles.ps1
```

1. **`01`** zips `hostedagents\a2ui-response` and `hostedagents\a2ui-stream` (only the `.csproj` and `.cs` files, flat at the zip root), then deploys `create_hostedagents.bicep`. A deployment script in Azure uploads each zip to the Foundry Agent Service and polls until the version is `active`. Allow several minutes: Foundry runs `dotnet restore` and `dotnet publish` for each agent
2. **`02`** reads each agent's `instance_identity.principal_id` from Foundry and gives it the Azure AI User role on the Foundry resource, so the agent can call the chat model. Wait a few minutes after it finishes

Run `01` again after changing an agent's code. Foundry creates a new version. If the zip and settings are identical, it returns the existing version.

## How it works

`create_hostedagents.bicep` uses a `deploymentScript` (a short Azure CLI script in a temporary container) that calls the Agent Service REST API with a user-assigned identity that has the Azure AI User role.

For each agent it:

1. Decodes the zip from the parameter and checks its SHA-256 against the hash computed on your PC
2. Posts `multipart/form-data` to `<project endpoint>/agents?api-version=v1` with a `metadata` part and a `code` part. If the agent already exists (409), it posts to `.../agents/<name>` to add a new version
3. Polls `.../agents/<name>/versions/<n>` until `status` is `active`, or stops with the error if it is `failed`

The agent definition it sends (here for `a2ui-stream`):

```json
{
  "kind": "hosted",
  "protocol_versions": [{ "protocol": "invocations", "version": "2.0.0" }],
  "cpu": "0.5", "memory": "1.0Gi",
  "code_configuration": {
    "runtime": "dotnet_10",
    "entry_point": ["dotnet", "a2ui-stream.dll"],
    "dependency_resolution": "remote_build"
  },
  "environment_variables": { "AZURE_AI_MODEL_DEPLOYMENT_NAME": "gpt-4.1-mini" }
}
```

For `a2ui-response` the protocol is `responses`. `FOUNDRY_PROJECT_ENDPOINT` is set by the platform, so it is not listed.

## Check it worked

```powershell
$ep = "https://$env:TENANT_PREFIX.services.ai.azure.com/api/projects/$env:TENANT_PREFIX-FoundryProject"
$token = az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv

# a2ui-response: the Responses protocol
curl.exe -s -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{\"input\":\"Say hello in five words\"}' "$ep/agents/a2ui-response/endpoint/protocols/openai/responses?api-version=v1"

# a2ui-stream: AG-UI over the Invocations protocol (events arrive as they are written)
$body = '{\"threadId\":\"t1\",\"runId\":\"r1\",\"state\":{},\"messages\":[{\"id\":\"m1\",\"role\":\"user\",\"content\":\"Say hello in five words\"}],\"tools\":[],\"context\":[],\"forwardedProps\":{}}'
curl.exe -N -H "Authorization: Bearer $token" -H "Content-Type: application/json" -H "Accept: text/event-stream" -d $body "$ep/agents/a2ui-stream/endpoint/protocols/invocations?api-version=v1"
```

The first returns a `completed` response with text. The second streams `data:` lines with `RUN_STARTED`, `TEXT_MESSAGE_CONTENT` and `RUN_FINISHED` events. Then run the Backend API against Foundry as described in the [main README](../README.md).

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `AuthorizationFailed` on a role | You need Owner, or Contributor plus User Access Administrator |
| HTTP 401 or 403 from the script | The script identity's new role is still taking effect. The script retries for about six minutes. Run `01` again if it gave up |
| `Provisioning failed` with a build error | The message shows the restore or compile error from the remote build. Fix the code and run `01` again |
| Stuck in `creating` for over 10 minutes | The remote build is slow. The Foundry docs suggest bundled mode (`dependency_resolution: bundled`, with `dotnet publish` output zipped) as the fix |
| The `invocations` protocol is rejected when the agent is created | Invocations may not be available for hosted agents in your region or subscription yet. Check the current Foundry hosted agent documentation |
| `424 session_not_ready` when calling | The agent crashed at startup, or did not answer `GET /readiness` on port 8088. See [../hostedagents/README.md](../hostedagents/README.md) |
| 401 or 403 when the agent calls the model | Run `02`, then wait a few minutes for the role to take effect |
| `AuthorizationFailed` for Microsoft.ContainerInstance | `01` registers that provider. You need permission to register providers on the subscription |

## Notes

- **Preview**: Hosted Agents and their REST API are preview. The request shape follows the current code-deploy documentation (api-version `v1`), so check it against the Foundry docs before relying on it
- **Verified**: `01_deploy-hostedagents.ps1` deployed both agents. Foundry reported each as `active`, `a2ui-response` registered with `responses` 2.0.0 and `a2ui-stream` with `invocations` 2.0.0. A call to each worked, and so did the Backend API against both. `02_create-hostedagentroles.ps1` was not needed in that project, because the agents could already call the model (the roles had been assigned earlier). It is there for a project where they have not
- **Time**: Foundry builds each agent in about a minute. The Bicep `deploymentScript` adds a few more minutes, because Azure starts a temporary container and storage account to run it
- **Foundry stays public**: this deployment needs public access to the Foundry data plane. If you lock Foundry down, run these scripts first
