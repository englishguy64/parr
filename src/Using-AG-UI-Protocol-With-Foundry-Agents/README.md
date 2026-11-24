# Using AG-UI Protocol with Foundry Agents

AG-UI is a new protocol for communicating with Foundry Agents for specific use cases. It complements REST rather than replacing it. REST is still the right choice for a simple request that needs one complete answer. AG-UI is for the cases where the user should see the agent work: streaming text, live progress, and a person approving an action.

A web page speaks AG-UI to a Backend, and the Backend speaks AG-UI to the page and calls the Microsoft Foundry agents that already exist. There is no APIM in this recipe: the page calls the Backend directly. This README explains how the pieces work together. For the Foundry agents themselves, see [Use an Azure Web App to Call Foundry Agents via Azure APIM](../Use-An-Azure-Web-App-To-Call-Foundry-Agents-Via-Azure-APIM/README.md).

## Overview

- **Website** - one page with three AG-UI use cases and a live list of every event. Speaks AG-UI with `fetch` and Server-Sent Events, no library and no build step
- **Backend** (ASP.NET, .NET 10) - one AG-UI endpoint per use case. Calls the Foundry agents with its own identity
- **Hosted agents** (2, in Foundry) - `agui-support` and `agui-research`, in the `hostedagents` folder. They deploy from source with the Foundry Toolkit for VS Code, with no container. The Backend creates nothing in Foundry: it calls these agents by name

## Architecture

```text
Browser
  │ 1. POST /agui/<use case>   {threadId, runId, messages}   Accept: text/event-stream
  ▼
Backend (AG-UI server) ── DefaultAzureCredential / managed identity
  │ 2. runs the Foundry agent named in the app settings
  ▼
Foundry project
  ├── support   → agui-support    (hosted agent)   chat and approval
  └── research  → agui-research   (hosted agent)   progress

Browser ◄── 3. RUN_STARTED · TEXT_MESSAGE_START / CONTENT / END · TOOL_CALL_* · RUN_FINISHED
```

## Folders

| Folder | Purpose |
|--------|---------|
| `azure` | Bicep and PowerShell that deploy the two hosted agents from source. See [azure/README.md](azure/README.md) |
| `hostedagents` | The two Foundry hosted agents, `agui-support` and `agui-research`. See [hostedagents/README.md](hostedagents/README.md) |
| `backend` | The AG-UI server: `Program.cs` (endpoints), `ApprovalGateAgent.cs` (human in the loop), `StubChatClient.cs` (local stand-in for Foundry) |
| `website` | The page: `index.html`, `app.js`, `styles.css` and `config.json`. Plain static files, no server code |

## The use cases

| Use case | Endpoint | Agent | What AG-UI adds over REST |
|----------|----------|-------|---------------------------|
| Stream a chat answer | `/agui/chat` | support | Text arrives word by word instead of after a long wait |
| Show live agent progress | `/agui/progress` | research | The page shows each stage of the run and every event, not a spinner |
| Approve before an action | `/agui/approval` | support | The run pauses until a person decides, then resumes |

## Key Features

- **One protocol for the page and the backend**: the same event stream drives the text, the progress strip and the approval prompt
- **Existing agents**: the Backend refers to the Foundry agents by name (an `AgentReference`). Nothing is created or changed in Foundry
- **No secrets in the browser**: the page only knows the Backend's address. The Backend calls Foundry with `DefaultAzureCredential` (your `az login` locally, a managed identity in Azure)
- **The client owns the conversation**: every run sends the whole `messages` list, so the Backend keeps no chat state
- **Human in the loop without server state**: the pause is an interrupt on the run, and the decision is a new run that carries it
- **Works without Azure**: with no Foundry settings the Backend uses a stub that streams a canned answer

## Walkthrough

One run, from the page to the answer. The numbers match the architecture above.

### 1. The page starts a run

`website/app.js` loads `config.json` (the Backend address, no secret). When you press Send it posts to `{backend}/agui/<use case>`:

```json
{ "threadId": "…", "runId": "…", "messages": [{ "id": "…", "role": "user", "content": "…" }],
  "state": {}, "tools": [], "context": [], "forwardedProps": {} }
```

with `Accept: text/event-stream`. The page keeps one `threadId` and one `messages` list per use case, and "New conversation" starts a fresh thread.

### 2. The Backend runs the agent

`backend/Program.cs` registers three endpoints with `MapAGUIServer`. Each wraps an agent:

| Endpoint | Agent |
|----------|-------|
| `/agui/chat` | the Foundry agent named in `AGENT_SUPPORT` |
| `/agui/progress` | the Foundry agent named in `AGENT_RESEARCH` |
| `/agui/approval` | `ApprovalGateAgent`, wrapping the support agent |

`project.AsAIAgent(new AgentReference(name))` turns an existing Foundry agent into an agent the AG-UI server can run. The Foundry call uses the project's Responses endpoint with that agent reference.

### 3. Events stream back

The AG-UI server turns what the agent produces into events, each sent as `data: {json}` followed by a blank line:

| Event | Meaning |
|-------|---------|
| `RUN_STARTED` | The run began |
| `TEXT_MESSAGE_START` / `TEXT_MESSAGE_CONTENT` / `TEXT_MESSAGE_END` | A message, with the text in `delta` pieces |
| `TOOL_CALL_START` / `TOOL_CALL_ARGS` / `TOOL_CALL_END` | The agent calls a tool |
| `RUN_FINISHED` | The run ended. `outcome.type` is `success` or `interrupt` |
| `RUN_ERROR` | The run failed |

The page reads the stream, appends each `delta` to the answer, lights the progress steps and adds a row to the event list. Idle streams carry `: keepalive` comment lines, which the page ignores.

### 4. Human in the loop

A Foundry agent that already exists owns its own tools, so a client-side tool that needs approval can't be added to it at request time. `ApprovalGateAgent` wraps the agent and puts the approval in front of the action instead:

1. **Run 1**: the support agent drafts a customer reply, which streams as normal text. The gate then asks for approval to call the tool `send_customer_reply`. The stream carries `TOOL_CALL_START / ARGS / END` and ends with `RUN_FINISHED` whose `outcome` is `{"type":"interrupt","interrupts":[{"id":"…","reason":"tool_call", …}]}`
2. The page shows **Approve** and **Reject**. The run is paused
3. **Run 2**: the page posts a new run on the same `threadId`, with no new messages, and the decision:

   ```json
   { "threadId": "…", "runId": "…", "messages": [],
     "resume": [{ "interruptId": "…", "status": "resolved", "payload": { "approved": true } }] }
   ```
4. The gate reads the decision. Approved gives "the reply was sent" (simulated: nothing leaves this demo). Rejected, or a cancelled interrupt, gives "nothing was sent"

The server keeps no state between the two runs. The decision is all the second run needs.

### Example: "Draft a reply about ORD-1001"

1. On **Approve before an action**, send the example message
2. The draft streams in and the Approval box appears: "The agent wants to call `send_customer_reply`"
3. Press **Approve**. A second run starts and the answer shows "Approved. The reply was sent…"

## Running it

### Prerequisites

- The [.NET 10 SDK](https://dotnet.microsoft.com/download) for the Backend (`dotnet --version` should show 10.x)
- Any static file server for the Website. The examples use Python (`python --version`). Node (`npx serve`) works too
- Two terminals, one for the Backend and one for the Website
- For real Foundry agents only: the Azure CLI, and the two hosted agents deployed with the scripts in [azure/README.md](azure/README.md)

### 1. Run with the stub (no Azure needed)

Start the Backend first, because the page calls it.

**Terminal 1: Backend** (listens on `http://localhost:5100`)

```powershell
cd src\Using-AG-UI-Protocol-With-Foundry-Agents\backend
dotnet run
```

Check it is up: open `http://localhost:5100/health` in a browser. You should see `{"status":"ok","foundry":false}`. `foundry` is `false` because no Foundry settings are set, so the Backend streams a canned answer.

**Terminal 2: Website** (listens on `http://localhost:5080`)

```powershell
cd src\Using-AG-UI-Protocol-With-Foundry-Agents\website
python -m http.server 5080
```

Open `http://localhost:5080`. The Website is only static files, so any static file server works.

Then try each use case:

1. **Stream a chat answer**: press **Send**. The text appears word by word
2. **Show live agent progress**: press **Send**. The progress steps light up and the event list fills
3. **Approve before an action**: press **Send**, wait for the Approval box, then press **Approve** or **Reject**

Stop either program with `Ctrl+C`.

### 2. Run against your real Foundry agents

Stop the Backend (`Ctrl+C`), set the Foundry settings in the same terminal, and start it again. The Website needs no change.

```powershell
az login
$env:FOUNDRY_PROJECT_ENDPOINT = 'https://<foundry>.services.ai.azure.com/api/projects/<project>'
$env:AGENT_SUPPORT  = 'agui-support'
$env:AGENT_RESEARCH = 'agui-research'
cd src\Using-AG-UI-Protocol-With-Foundry-Agents\backend
dotnet run
```

- Your user needs the **Azure AI User** role on the Foundry resource
- Foundry must still allow public access, or you must run the Backend from inside the VNet
- All three settings must be set. `http://localhost:5100/health` shows `"foundry":true` when the Backend is using Foundry
- The environment variables last only for that terminal window

### 3. Use different ports

The Backend's port is set in `backend\Properties\launchSettings.json`, and the Website's port is the number you give the file server. To use others, pass `--urls` to the Backend, tell it which website to allow, and edit `website\config.json`:

```powershell
# Backend on 6100, allowing a website on 6080
$env:ALLOWED_ORIGINS = 'http://localhost:6080'
dotnet run --urls http://localhost:6100

# Website on 6080
python -m http.server 6080
```

Then set `"backendUrl": "http://localhost:6100"` in `website\config.json`.

## Configuration

| Component | Setting | Purpose |
|-----------|---------|---------|
| Website (`config.json`) | `backendUrl` | Address of the Backend. Default `http://localhost:5100` |
| Backend | `FOUNDRY_PROJECT_ENDPOINT` | Foundry project address. Empty runs the stub |
| Backend | `AGENT_SUPPORT` / `AGENT_RESEARCH` | Foundry agent behind "support" and "research". All three Foundry settings must be set, or the stub is used |
| Backend | `ALLOWED_ORIGINS` | Website addresses allowed by CORS, comma separated. Default `http://localhost:5080` |

None of these is a secret. In App Service, give the Backend a managed identity with the Azure AI User role on the Foundry resource, set the Backend's `ALLOWED_ORIGINS` to the website's address, and set `backendUrl` in the website's `config.json` to the Backend's address. The Website can go on any static host, for example Azure Static Web Apps or a Blob Storage static website.

## Security

- ✅ No secret in the browser: the page holds only the Backend address
- ✅ The Backend calls Foundry with its own identity, never with a key
- ✅ CORS only allows the websites in `ALLOWED_ORIGINS`
- ⚠️ The Backend has no sign-in. Anyone who can reach it spends your Foundry quota. Put Entra ID sign-in in front of it before exposing it, as the other recipe does
- ⚠️ The approval step is the only control on the "send" action. In a real system, enforce permissions on the server when the action runs, not only in the page

## Troubleshooting

| Issue | Solution |
|-------|----------|
| The page says "The call failed. Is the backend running?" | Start the Backend, and check `backendUrl` in `config.json` |
| Browser console shows a CORS error | Add the website's address to the Backend's `ALLOWED_ORIGINS` |
| The answer is a stub message | `FOUNDRY_PROJECT_ENDPOINT`, `AGENT_SUPPORT` and `AGENT_RESEARCH` must all be set. Check `/health` |
| 401 or 403 from Foundry in the Backend log | Run `az login`, and give the identity the Azure AI User role. A new role can take a few minutes |
| Agent not found | `AGENT_*` must be the Foundry agent's name, not a display name |
| Text arrives in one lump | A proxy or gateway is buffering the response. Turn response buffering off |
| A long run is cut off | An idle or total timeout on a proxy or App Service front end. Raise it or shorten the run |
| Approve does nothing | The run must have ended with an interrupt. Check the event list for `RUN_FINISHED` with outcome `interrupt` |

## Customization

### Use different agents

Change `AGENT_SUPPORT` and `AGENT_RESEARCH` to the names of any agents in the project, hosted or prompt. The Backend calls each agent through its own endpoint, which serves both kinds.

### Change the approved action

Edit `ApprovalGateAgent.cs`. `ToolName` is the tool the page is asked to approve, and the text returned after the decision is in `RunCoreStreamingAsync`. Replace the simulated "sent" with a call to your own system.

### Add a use case

1. In `backend/Program.cs`, add `app.MapAGUIServer("/agui/<name>", agent);`
2. In `website/app.js`, add an entry to `cases` with its `path`, `about` and `example`
3. In `website/index.html`, add a tab button with `data-case="<name>"`

## Validation

```powershell
dotnet build backend
```

## Notes

- **Preview packages**: `Microsoft.Agents.AI.Hosting.AGUI.AspNetCore` and `Microsoft.Agents.AI.Foundry` are preview and will change. Check the API against the current [AG-UI documentation](https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/ui/ag-ui/?pivots=programming-language-csharp#when-to-use-ag-ui) before relying on it
- **Verified**: streaming, progress events and the approve, reject and cancel paths were run end to end against the stub. Calls to real Foundry agents were not run from this repository, so test them with your own project
