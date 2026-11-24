# Hosted agents

Two Foundry Hosted Agents for the AG-UI recipe. They deploy **from source**: no Dockerfile, no container registry. A tool zips the project folder, and Foundry runs `dotnet restore` and `dotnet publish` for you. Use the scripts in [../azure](../azure/README.md) (recommended) or the Foundry Toolkit for VS Code.

All agent names start with `agui-`.

| Folder | Agent name | Used by | What it does |
|--------|------------|---------|--------------|
| `agui-support` | `agui-support` | `/agui/chat` and `/agui/approval` | Answers support questions in at most three sentences |
| `agui-research` | `agui-research` | `/agui/progress` | English tutor: lists each grammar fix and explains it |

Each agent is a small ASP.NET app (`Program.cs`) that creates a chat agent on a model in the same Foundry project and hosts it with `AddFoundryResponses` and `MapFoundryResponses`. Foundry calls the Responses protocol on port 8088. The agents speak Responses, not AG-UI: the Backend turns their output into AG-UI events for the website.

`azure.yaml` declares both services (runtime `dotnet_10`, remote build) for the Toolkit and `azd`. The scripts in `../azure` do not read it: they take the same settings from `create_hostedagents.bicep` and `01_deploy-hostedagents.ps1`.

## Before you deploy

- A Foundry project with a chat model deployment (the examples use `gpt-4.1-mini`)
- `az login`, and permission to create agents in the project (Azure AI User at minimum)
- For the Toolkit route only: the [Foundry Toolkit for VS Code](https://code.visualstudio.com/docs/intelligentapps/hosted-agents) extension

If your model deployment has another name, pass `-ModelDeployment` to `01_deploy-hostedagents.ps1`, or change `AZURE_AI_MODEL_DEPLOYMENT_NAME` in `azure.yaml` for the Toolkit.

## Deploy with the scripts (recommended)

The Foundry Toolkit wizard registered these agents with the Responses protocol at 1.0.0, but the code serves 2.0.0, so calls fail. The Bicep and PowerShell scripts in [../azure/README.md](../azure/README.md) deploy both agents with 2.0.0:

```powershell
cd ..\azure
.\01_deploy-hostedagents.ps1
.\02_create-hostedagentroles.ps1    # only if the agents get an authorization error calling the model
```

## Or deploy with the Foundry Toolkit

**Known problem:** in my run the Toolkit wizard registered the agents with the Responses protocol at **1.0.0**, and calls failed with `501 Unsupported responses protocol version`. A newer Toolkit may register 2.0.0, so check the agent's protocol version after deploying (the Foundry portal or `GET <project endpoint>/agents/<name>?api-version=v1` shows `protocol_versions`). If it says 1.0.0, use the scripts above instead.

Do this once for each agent folder.

1. Open the `hostedagents` folder in VS Code
2. In the Foundry Toolkit, choose **Deploy Hosted Agent**
3. Choose your Foundry project
4. Choose the **Code** deployment type (not Container), the **Remote** package mode, and the **.NET 10** runtime
5. Choose **New agent** and enter the name: `agui-support` for the first, `agui-research` for the second
6. Point it at the agent's folder (`agui-support` or `agui-research`) and finish the wizard

To release a change later, deploy again and choose **Existing agent**. Foundry creates a new version.

The Toolkit may create or adjust `azure.yaml` as it goes. The hosted agent tooling is in preview, so check what it generates against the file here.

## Run one on your PC

```powershell
az login
$env:FOUNDRY_PROJECT_ENDPOINT = 'https://<foundry>.services.ai.azure.com/api/projects/<project>'
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = 'gpt-4.1-mini'
cd agui-support
dotnet run --urls http://localhost:8088
```

Then, from another terminal:

```powershell
$body = '{"input":"Where is my order?"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8088/responses -ContentType 'application/json' -Body $body
```

`GET http://localhost:8088/readiness` returns 200 when the agent is up. Your user needs the Azure AI User role on the Foundry resource.

## Connect the Backend

Set the Backend's agent names to the hosted agents, then run it as described in the [main README](../README.md):

```powershell
$env:AGENT_SUPPORT  = 'agui-support'
$env:AGENT_RESEARCH = 'agui-research'
```

The Backend calls each agent through its own endpoint, `<project endpoint>/agents/<name>/endpoint/protocols/openai`.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `424 session_not_ready` when the agent is called | The agent crashed at startup, or `/readiness` did not return 200 in time. Read the startup log (below) to see which. Two causes seen so far: `builder.Services.AddFoundryResponses(...)` throws in a hosted Foundry environment (use `builder.AddFoundryResponses(...)` on the host builder), and the app must listen on port 8088 (each `Program.cs` binds `PORT`, because a source deployment has no Dockerfile to set it). Redeploy with **Existing agent** after changing the code |
| The call takes about a minute, then fails | Same cause: Foundry waits for the session to become ready, then gives up |
| `501 Unsupported responses protocol version. This agent requires responses protocol v2.0.0` | The agent was registered with protocol 1.0.0, for example by the Toolkit wizard. Deploy again with the scripts in `../azure`, which register 2.0.0 |
| Still failing after redeploying | Check the agent's logs in the Foundry portal or the Toolkit. A startup error shows there, for example a missing model deployment or no access to the project |

### Read the startup log

A failed call returns an `x-agent-session-id` header. Stream that session's log (replace the placeholders):

```powershell
$token = az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv
curl.exe -N -H "Authorization: Bearer $token" -H "Accept: text/event-stream" "<project endpoint>/agents/agui-support/versions/<version>/sessions/<session id>:logstream?api-version=v1"
```

Look for `stderr` lines. An unhandled exception at startup is shown there with its stack trace.

## Notes

- **Preview**: Hosted Agents and the packages (`Microsoft.Agents.AI.Foundry.Hosting`, `Microsoft.Agents.AI.Foundry`) are preview. Check against the current documentation before relying on them
- **Tested against Foundry**: deployed with the scripts in `../azure` and called directly and through the backend over AG-UI. Not tested with the Toolkit wizard, which registered protocol 1.0.0 in my run
- **Names**: an agent name must start and end with a letter or digit, may contain hyphens, and can be at most 63 characters
- **Why hosted?** Instructions-only agents also work as Prompt Agents. A hosted agent is the right choice once an agent needs your own code, for example calling your order system
