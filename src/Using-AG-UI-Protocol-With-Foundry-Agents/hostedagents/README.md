# Hosted agents

Two Foundry Hosted Agents for the AG-UI recipe. They deploy **from source**: no Dockerfile, no container registry. The Foundry Toolkit for VS Code zips the project folder, and Foundry runs `dotnet restore` and `dotnet publish` for you.

All agent names start with `agui-`.

| Folder | Agent name | Used by | What it does |
|--------|------------|---------|--------------|
| `agui-support` | `agui-support` | `/agui/chat` and `/agui/approval` | Answers support questions in at most three sentences |
| `agui-research` | `agui-research` | `/agui/progress` | English tutor: lists each grammar fix and explains it |

Each agent is a small ASP.NET app (`Program.cs`) that creates a chat agent on a model in the same Foundry project and hosts it with `AddFoundryResponses` and `MapFoundryResponses`. Foundry calls the Responses protocol on port 8088. The agents speak Responses, not AG-UI: the Backend turns their output into AG-UI events for the website.

`azure.yaml` declares both services (runtime `dotnet_10`, remote build) for the Toolkit and `azd`.

## Before you deploy

- A Foundry project with a chat model deployment (the examples use `gpt-4.1-mini`)
- The [Foundry Toolkit for VS Code](https://code.visualstudio.com/docs/intelligentapps/hosted-agents) extension, and `az login`
- Your user needs permission to create agents in the project (Azure AI User at minimum)

If your model deployment has another name, change `AZURE_AI_MODEL_DEPLOYMENT_NAME` in `azure.yaml`.

## Deploy with the Foundry Toolkit

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
| `424 session_not_ready` when the agent is called | Foundry's `/readiness` check did not get a 200 within the timeout. The agent must listen on port 8088. Each `Program.cs` binds `PORT` (8088) in code because a source deployment has no Dockerfile to set it. Redeploy with **Existing agent** after changing it |
| The call takes about a minute, then fails | Same cause: Foundry waits for the session to become ready, then gives up |
| Still failing after redeploying | Check the agent's logs in the Foundry portal or the Toolkit. A startup error shows there, for example a missing model deployment or no access to the project |

## Notes

- **Preview**: Hosted Agents and the packages (`Microsoft.Agents.AI.Foundry.Hosting`, `Microsoft.Agents.AI.Foundry`) are preview. Check against the current documentation before relying on them
- **Not tested against Foundry**: both projects build, and each hosts `/responses` and `/readiness` on port 8088 locally. They have not been deployed or called against a real Foundry project from this repository
- **Names**: an agent name must start and end with a letter or digit, may contain hyphens, and can be at most 63 characters
- **Why hosted?** Instructions-only agents also work as Prompt Agents. A hosted agent is the right choice once an agent needs your own code, for example calling your order system
