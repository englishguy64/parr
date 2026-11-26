# Hosted agents

Two Foundry Hosted Agents for the A2UI recipe, written in C#. They deploy **from source**: no Dockerfile, no container registry. A script zips the project folder, and Foundry runs `dotnet restore` and `dotnet publish` for you. Use the scripts in [../azure](../azure/README.md).

The two agents return their data over different protocols, and the Backend API has a translator for each:

| Folder | Agent name | Returns data via | Called by the Backend API for | Translator |
|--------|------------|------------------|-------------------------------|------------|
| `a2ui-response` | `a2ui-response` | **Responses protocol** | `POST /api/a2ui/response` | Responses To A2UI |
| `a2ui-stream` | `a2ui-stream` | **AG-UI protocol** | `POST /api/a2ui/stream` | AG-UI To A2UI |

Both create a chat agent on a model in the same Foundry project, and both are told to answer in plain text, because the Backend API decides how the answer looks on screen by turning it into A2UI components.

## a2ui-response

`Program.cs` hosts the agent with `AddFoundryResponses` and `MapFoundryResponses`. Those provide `POST /responses` and `GET /readiness` on port 8088, which is everything Foundry needs. It is registered with the **responses** protocol, version 2.0.0.

## a2ui-stream

Foundry has no AG-UI protocol of its own. Its hosted agent contract asks a container to listen on port 8088, answer `GET /readiness` with 200, and serve at least one of `POST /responses`, `POST /invocations` or `POST /activity/messages`. The **Invocations** protocol is a pass-through: Foundry hands the request body to the agent untouched, and the agent may answer with raw Server-Sent Events. That is what AG-UI needs, so this agent:

1. Serves AG-UI at `POST /invocations` using `AddAGUIServer` and `MapAGUIServer("/invocations", agent)`. It reads an AG-UI run request and writes AG-UI events (`RUN_STARTED`, `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT` for each piece of text, `TEXT_MESSAGE_END`, `RUN_FINISHED`)
2. Adds its own `GET /readiness`, because the Responses hosting package that normally provides it is not used here
3. Is registered with the **invocations** protocol, version 2.0.0. Foundry then forwards `POST <project>/agents/a2ui-stream/endpoint/protocols/invocations` to `/invocations`

If `FOUNDRY_PROJECT_ENDPOINT` is not set, it uses a stub chat client (`StubChatClient.cs`) instead of a model, so you can try the AG-UI endpoint on your PC without Azure.

## Run them on your PC

### a2ui-stream without Azure

```powershell
cd a2ui-stream
dotnet run
```

In another terminal, post an AG-UI run request and watch the events arrive:

```powershell
$body = '{"threadId":"t1","runId":"r1","state":{},"messages":[{"id":"m1","role":"user","content":"hello"}],"tools":[],"context":[],"forwardedProps":{}}'
curl.exe -N -H "Content-Type: application/json" -H "Accept: text/event-stream" -d $body http://localhost:8088/invocations
```

`GET http://localhost:8088/readiness` returns 200.

To send the whole recipe through it, start the Backend API with the local agent's address (no sign-in is used for it):

```powershell
$env:AGENT_STREAM_URL = 'http://localhost:8088/invocations'
cd ..\..\backendapi
dotnet run
```

### With a real model

Both agents can use a chat model in your Foundry project. Your user needs the Azure AI User role on the Foundry resource:

```powershell
az login
$env:FOUNDRY_PROJECT_ENDPOINT = 'https://<foundry>.services.ai.azure.com/api/projects/<project>'
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = 'gpt-4.1-mini'
cd a2ui-response      # or a2ui-stream
dotnet run
```

For `a2ui-response`, post to `http://localhost:8088/responses`:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8088/responses -ContentType 'application/json' -Body '{"input":"Say hello in five words"}'
```

## Deploy

```powershell
cd ..\azure
.\01_deploy-hostedagents.ps1
.\02_create-hostedagentroles.ps1    # only if the agents get an authorization error calling the model
```

See [../azure/README.md](../azure/README.md). Then run the Backend API against Foundry as described in the [main README](../README.md).

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `424 session_not_ready` when an agent is called | The agent crashed at startup, or `/readiness` did not return 200 on port 8088 in time. Both `Program.cs` files bind port 8088, because a source deployment has no Dockerfile to set it. `a2ui-response` must use `builder.AddFoundryResponses(...)` on the host builder, not on `builder.Services` |
| `501 Unsupported ... protocol version` | The agent was registered with a different protocol version than the code serves. Deploy again with the scripts in `../azure` |
| `404` or `405` on `.../protocols/invocations` | The agent was not registered with the invocations protocol, or Invocations is not available in your region. The Invocations WebSocket variant is region limited in preview, so check the current documentation |
| 401 or 403 when an agent calls the model | Run `02_create-hostedagentroles.ps1`, then wait a few minutes for the role to take effect |

To read a failed session's startup log, see [the same steps in the AG-UI recipe](../../Using-AG-UI-Protocol-With-Foundry-Agents/hostedagents/README.md#read-the-startup-log).

## Notes

- **Preview**: Hosted Agents, the Invocations protocol and the packages (`Microsoft.Agents.AI.Foundry`, `Microsoft.Agents.AI.Foundry.Hosting`, `Microsoft.Agents.AI.Hosting.AGUI.AspNetCore`) are preview. Check against the current documentation before relying on them
- **What was tested**: both projects build, and `a2ui-stream` was run locally with the stub, answering `/readiness` with 200 and streaming AG-UI events from `/invocations`. The Backend API's AG-UI To A2UI translator was run against it. **Nothing has been deployed to Foundry from this recipe**, so the Foundry side (the Invocations registration, the address Foundry forwards, caller sign-in) is untested. `a2ui-response` follows the same pattern as the `agui-support` agent in the AG-UI recipe, which was deployed to Foundry
- **Names**: an agent name must start and end with a letter or digit, may contain hyphens, and can be at most 63 characters
- **Why hosted?** A Prompt Agent only speaks the Responses protocol. An agent that returns data over AG-UI has to be a Hosted Agent, because it is your own code serving the protocol
