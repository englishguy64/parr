// a2ui-stream: a Foundry Hosted Agent that RETURNS ITS DATA VIA THE AG-UI PROTOCOL. The Backend API calls it for
// POST /api/a2ui/stream and turns each AG-UI event into an A2UI message (the "AG-UI To A2UI" translator).
//
// Hosted Agents are your own code running in Foundry Agent Service. This one deploys from source (no container, no registry):
// the scripts in ../../azure zip this folder and Foundry runs `dotnet restore` and `dotnet publish`.
//
// The platform contract for a hosted agent (see the Foundry "hosted agent runtime contract"):
//   - listen on port 8088
//   - answer GET /readiness with 200
//   - serve a protocol endpoint. AG-UI is not a Foundry protocol of its own, so this agent registers the INVOCATIONS protocol,
//     which passes any JSON body through and lets the agent stream raw Server-Sent Events. The agent serves AG-UI there:
//     POST /invocations takes an AG-UI run request and answers with AG-UI events (RUN_STARTED, TEXT_MESSAGE_CONTENT, ...).
//
// Settings:
//   FOUNDRY_PROJECT_ENDPOINT          set by the platform when deployed. Locally: https://<foundry>.services.ai.azure.com/api/projects/<project>
//                                     (empty: run with a stub chat client so the AG-UI endpoint can be tried without Azure)
//   AZURE_AI_MODEL_DEPLOYMENT_NAME    chat model deployment to use (default gpt-4.1-mini). Set by the deployment script
//
// Run it on your PC: dotnet run, then POST http://localhost:8088/invocations (see ../README.md).
//
// The AG-UI and Foundry packages are preview: check the API against the current documentation before relying on it.
using Azure.AI.Projects;
using Azure.Identity;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Hosting.AGUI.AspNetCore;

var projectEndpoint = Environment.GetEnvironmentVariable("FOUNDRY_PROJECT_ENDPOINT");
var deployment = Environment.GetEnvironmentVariable("AZURE_AI_MODEL_DEPLOYMENT_NAME") ?? "gpt-4.1-mini";
const string instructions = "You are a calm, concise English assistant. Answer in plain text only, with no Markdown, in at most four short sentences.";

AIAgent agent = !string.IsNullOrEmpty(projectEndpoint)
    ? new AIProjectClient(new Uri(projectEndpoint), new DefaultAzureCredential())
        .AsAIAgent(model: deployment, instructions: instructions, name: "a2ui-stream",
                   description: "Answers a question as a stream of AG-UI text events.")
    : new ChatClientAgent(new StubChatClient(), name: "a2ui-stream");

var builder = WebApplication.CreateBuilder(args);

// Port 8088, as the contract requires. A container image sets this in its Dockerfile; deploying from source has none.
builder.WebHost.UseUrls($"http://0.0.0.0:{Environment.GetEnvironmentVariable("PORT") ?? "8088"}");
builder.Services.AddAGUIServer();

var app = builder.Build();

// The health probe. The Responses hosting package registers this for you; an AG-UI app has to do it itself.
app.MapGet("/readiness", () => Results.Ok());

// The protocol endpoint: AG-UI over the Invocations protocol. Foundry forwards POST .../protocols/invocations to /invocations.
app.MapAGUIServer("/invocations", agent);

app.Run();
