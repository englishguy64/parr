# Receive A2UI Components Into Angular Website From Foundry Agents

> With A2UI, the agent describes what to show, and every app draws the UI with its own native components. The application receives A2UI messages and each app renders the content securely and at native speed. Users get the same low latency, high trust, and complete native fidelity whether they reach a company's agent in its own app or in a third-party AI assistant that hosts MCP apps, such as Gemini or Claude.
>
> From Google, the [A2UI home page](https://a2ui.org)

A2UI (Agent-to-UI) is an open protocol from Google that lets an agent describe a user interface as data. The Angular website does not receive HTML. It receives small JSON messages and builds real Angular components from them, using a catalog of components it already trusts (Text, Card, Column, Button and so on).

In this recipe an Angular website asks a question and a C# Backend API calls a Foundry agent. Two Foundry agents are used, and each returns its data over a different protocol: one **via the Responses protocol**, the other **via the AG-UI protocol**. The Backend API has one translator for each, and both produce A2UI messages that the website renders. Both Foundry agents are written in C# in the `hostedagents` folder, and the `azure` folder has Bicep and PowerShell that deploy them from source, with no container.

## Overview

- **Website** (`website/`, Angular) - a question box, two buttons, the rendered A2UI card and a live list of every A2UI message received. Uses the `@a2ui/angular` renderer with the Basic catalog
- **Backend API** (`backendapi/`, ASP.NET, .NET 10) - two endpoints, one per agent, and two translators: **A2UIFromResponse** and **A2UIFromAGUI**. Calls Foundry with its own identity
- **Foundry hosted agents** (2, C#, deployed from source):
  - `a2ui-response` - **returns data via the Responses protocol**
  - `a2ui-stream` - **returns data via the AG-UI protocol**. Foundry has no AG-UI protocol of its own, so it serves AG-UI over the Invocations protocol, see [hostedagents/README.md](hostedagents/README.md)

## Architecture

```text
Angular website (A2UI renderer)
  | POST /api/a2ui/response  {prompt, surfaceId}      one JSON array of A2UI messages back
  | POST /api/a2ui/stream    {prompt, surfaceId}      one A2UI message per line back, as they are produced
  v
C# Backend API -- DefaultAzureCredential / managed identity
  +-- A2UIFromResponse translator    <-- Responses protocol -- a2ui-response   one complete text answer
  +-- A2UIFromAGUI translator        <-- AG-UI protocol ------ a2ui-stream     AG-UI events: text deltas as they are written
                  |
                  v
              A2UI messages --> website
```

Foundry never sends the website anything. The Backend API calls each agent, translates what comes back into A2UI messages, and the website only ever sees A2UI.

## Folders

| Folder | Purpose |
|--------|---------|
| `backendapi` | `Program.cs` (the two endpoints), `A2UIMessages.cs` (the A2UI message builders), `A2UIFromResponse.cs` (the Responses protocol translator), `AGUIClient.cs` (calls the AG-UI agent and reads its events), `A2UIFromAGUI.cs` (the AG-UI translator), `StubChatClient.cs` (a local stand-in for Foundry) |
| `hostedagents` | The two Foundry hosted agents in C#: `a2ui-response` (Responses protocol) and `a2ui-stream` (AG-UI over the Invocations protocol). See [hostedagents/README.md](hostedagents/README.md) |
| `azure` | Bicep and PowerShell that deploy the two agents from source, no container. See [azure/README.md](azure/README.md) |
| `website` | The Angular app. `src/app/agent.service.ts` calls the Backend API and feeds every message to the A2UI renderer. `src/app/app.config.ts` sets up the renderer |

## The A2UI payload

The Backend API sends A2UI protocol version **v0.9**. Three message types build a card on the screen. Every message has a `version` and one message key.

**1. `createSurface`** makes an empty surface and names the catalog of components it may use:

```json
{
  "version": "v0.9",
  "createSurface": {
    "surfaceId": "stream-1",
    "catalogId": "https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json"
  }
}
```

**2. `updateComponents`** sends the component tree as a flat list. Components refer to their children by id, and the component with the id `root` is where rendering starts:

```json
{
  "version": "v0.9",
  "updateComponents": {
    "surfaceId": "stream-1",
    "components": [
      { "id": "root", "component": "Column", "children": ["card"] },
      { "id": "card", "component": "Card", "child": "body" },
      { "id": "body", "component": "Column", "children": ["heading", "agent", "answer", "divider", "status"] },
      { "id": "heading", "component": "Text", "variant": "h3", "text": "Streamed answer from the Streaming agent" },
      { "id": "agent", "component": "Text", "variant": "caption", "text": "Foundry agent: a2ui-stream" },
      { "id": "answer", "component": "Text", "variant": "body", "text": { "path": "/answer" } },
      { "id": "divider", "component": "Divider", "axis": "horizontal" },
      { "id": "status", "component": "Text", "variant": "caption", "text": { "path": "/status" } }
    ]
  }
}
```

`{ "path": "/answer" }` binds the text to the surface's data model. When the data changes, the text redraws. The component tree is never sent again.

**3. `updateDataModel`** sets the data. First the whole model, then one path at a time as the answer grows:

```json
{ "version": "v0.9", "updateDataModel": { "surfaceId": "stream-1", "path": "/", "value": { "answer": "", "status": "Streaming..." } } }
{ "version": "v0.9", "updateDataModel": { "surfaceId": "stream-1", "path": "/answer", "value": "Start with a" } }
{ "version": "v0.9", "updateDataModel": { "surfaceId": "stream-1", "path": "/answer", "value": "Start with a calm walk." } }
{ "version": "v0.9", "updateDataModel": { "surfaceId": "stream-1", "path": "/status", "value": "Complete in 2.3 s" } }
```

A2UI has no "append", so each streamed update carries the whole text so far.

### The two endpoints

| Endpoint | Agent and protocol | Translator | What comes back |
|---|---|---|---|
| `POST /api/a2ui/response` | `a2ui-response`, Responses protocol | A2UIFromResponse | One JSON array: `createSurface`, `updateComponents`, `updateDataModel`. Sent when the agent has finished |
| `POST /api/a2ui/stream` | `a2ui-stream`, AG-UI protocol | A2UIFromAGUI | Newline delimited JSON (`application/x-ndjson`): the surface and components first, then one `updateDataModel` per text delta, then a final status. Each line is flushed as it is produced |

How the AG-UI events become A2UI messages:

| AG-UI event from the agent | A2UI message to the website |
|---|---|
| (start of the run) | `createSurface`, `updateComponents`, `updateDataModel` on `/` |
| `TEXT_MESSAGE_CONTENT` with a `delta` | `updateDataModel` on `/answer` with the text so far |
| `RUN_FINISHED` | `updateDataModel` on `/status`: complete |
| `RUN_ERROR` | `updateDataModel` on `/status`: the error |

## Run it on your PC (no Azure needed)

With `FOUNDRY_PROJECT_ENDPOINT` unset, the Backend API uses stubs, so you can see the whole A2UI flow without Foundry. The stub for the Response agent returns a canned text answer. The stub for the AG-UI agent produces the same AG-UI events a real agent would (`RUN_STARTED`, `TEXT_MESSAGE_CONTENT` for each word, `RUN_FINISHED`), so the A2UIFromAGUI translator is exercised too.

1. Start the Backend API (it listens on http://localhost:5200):

   ```
   cd backendapi
   dotnet run
   ```

2. Start the website (it needs Node.js 22 or later):

   ```
   cd website
   npm install
   npm start
   ```

3. Open http://localhost:4200, press **Ask the Response agent** and **Ask the Streaming agent**. The card appears on the left, and the raw A2UI messages on the right.

`website/public/config.json` holds the Backend API address. Change `apiBase` if the API runs somewhere else.

## Run it against Foundry

1. Deploy the two hosted agents from the `azure` folder. They are plain C# projects, so nothing is built on your PC and there is no container:

   ```powershell
   $env:TENANT_PREFIX = '<prefix>'      # Foundry resource <prefix>, project <prefix>-FoundryProject, group <prefix>-rg1
   cd azure
   .\01_deploy-hostedagents.ps1
   .\02_create-hostedagentroles.ps1
   ```

   - **`a2ui-response`** returns data via the Responses protocol
   - **`a2ui-stream`** returns data via the AG-UI protocol. Foundry has no AG-UI protocol, so the agent serves AG-UI at `/invocations` and is registered with the Invocations protocol

   See [azure/README.md](azure/README.md). You can also use agents you already have: the names are settings, and `a2ui-response` can be any Prompt Agent or Hosted Agent that answers in text.
2. Sign in with `az login`. Your user needs the **Azure AI User** role on the Foundry resource. In App Service, give the app a managed identity with the same role.
3. Set the Backend API's settings, then run it:

   | Setting | Meaning |
   |---|---|
   | `FOUNDRY_PROJECT_ENDPOINT` | `https://<foundry>.services.ai.azure.com/api/projects/<project>` |
   | `AGENT_RESPONSE` | Name of the agent behind `/api/a2ui/response` (default `a2ui-response`) |
   | `AGENT_STREAM` | Name of the AG-UI agent behind `/api/a2ui/stream` (default `a2ui-stream`) |
   | `AGENT_STREAM_URL` | Optional, for local testing only: the address of an AG-UI agent on your PC, for example `http://localhost:8088/invocations`. Replaces the Foundry call, with no sign-in |
   | `ALLOWED_ORIGINS` | Website origins allowed by CORS (default `http://localhost:4200`) |

   ```
   $env:FOUNDRY_PROJECT_ENDPOINT = "https://<foundry>.services.ai.azure.com/api/projects/<project>"
   dotnet run
   ```

How each agent is called:

| Agent | Address the Backend API calls |
|---|---|
| Response | `<project>/agents/<name>/endpoint/protocols/openai` (Foundry Responses protocol) |
| AG-UI | `POST <project>/agents/<name>/endpoint/protocols/invocations?api-version=v1`, with an AG-UI run request in the body and `Accept: text/event-stream` |

**Tested against Foundry.** The two hosted agents were deployed with the scripts in `azure`. `a2ui-response` answered over the Responses protocol, `a2ui-stream` streamed AG-UI events over the Invocations protocol, and the Backend API turned both into A2UI messages (a complete answer, and a stream of messages ending in a status line). Hosted Agents, the Invocations protocol and the packages are preview, so check the details against the current documentation.

## Try the AG-UI agent on your PC

The `a2ui-stream` agent runs without Azure, using a stub chat client, so you can send the real AG-UI events through the Backend API's translator:

```powershell
# terminal 1: the AG-UI agent (listens on http://localhost:8088)
cd hostedagents\a2ui-stream
dotnet run

# terminal 2: the Backend API, pointed at it
$env:AGENT_STREAM_URL = 'http://localhost:8088/invocations'
cd backendapi
dotnet run
```

Then press **Ask the Streaming agent** on the website. The answer is the stub agent's canned text, streamed as AG-UI events and translated into A2UI messages.

## Design notes

- **The Backend API builds the UI, not the agent.** The agents return plain text. The Backend API decides which components to use, so a model can never send the website a component or a link you did not plan for. If you later let an agent produce A2UI itself, treat that output as untrusted input: validate it and keep to a catalog of components you trust.
- **The stream sends the layout once.** After that only the data changes, so each streamed message is tiny.
- **AG-UI streams, A2UI describes.** A2UI is the component format: what to show. AG-UI is a streaming protocol: how events arrive. Here AG-UI is used between the Foundry agent and the Backend API, and the Backend API turns its events into A2UI messages. The website receives only A2UI, one message per line of newline delimited JSON, so it never has to know which protocol an agent used. For an AG-UI event stream all the way to the browser, see the [Using AG-UI Protocol With Foundry Agents](../Using-AG-UI-Protocol-With-Foundry-Agents/README.md) recipe.
- **Preview software.** A2UI is young and the renderer packages (`@a2ui/angular` 0.16 here) and the Foundry packages are in preview. Message names differ between A2UI versions: this recipe uses v0.9 (`createSurface`, `updateComponents`, `updateDataModel`), and the website imports the v0.9 renderer from `@a2ui/angular/v0_9`. Check the current documentation before relying on any of it.

## Documentation

- [A2UI documentation](https://a2ui.org)
- [How to integrate A2UI into a client](https://a2ui.org/guides/client-integration/)
- [A2UI messages](https://a2ui.org/concepts/messages/)
