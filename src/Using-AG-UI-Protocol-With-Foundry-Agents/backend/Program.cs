// Backend: speaks AG-UI to the website and to Microsoft Foundry.
//
//   Website --(AG-UI: POST + Server-Sent Events)--> this backend --(Foundry Responses API)--> existing Foundry agents
//
// Three AG-UI endpoints, one per use case on the page. Each one wraps an agent that ALREADY EXISTS in the Foundry project.
// The agents are the Hosted Agents in ../hostedagents (agui-support and agui-research, deployed with the Foundry Toolkit for
// VS Code). Any Prompt Agent works too: the agent's own endpoint serves both kinds. Nothing is created in Foundry here:
//
//   POST /agui/chat       agui-support     streaming chat
//   POST /agui/progress   agui-research    live progress: the page shows every AG-UI event as it arrives
//   POST /agui/approval   agui-support     human in the loop: the agent drafts a reply, a person approves before it is sent
//   GET  /health
//
// Settings (App Service application settings, or environment variables locally):
//   FOUNDRY_PROJECT_ENDPOINT   https://<foundry>.services.ai.azure.com/api/projects/<project>
//                              (empty: run with a stub that streams a canned answer, nothing is sent to Azure)
//   AGENT_SUPPORT              Foundry agent name behind "chat" and "approval"   (agui-support)
//   AGENT_RESEARCH             Foundry agent name behind "progress"              (agui-research)
//   ALLOWED_ORIGINS            comma separated website origins for CORS, default http://localhost:5080
//
// Locally it signs in with your `az login` (DefaultAzureCredential). Your user needs the Azure AI User role on the Foundry
// resource. In App Service, give the app a managed identity with the same role.
//
// The AG-UI and Foundry packages are preview: check the API against the current documentation before relying on it.
using Azure.AI.Projects;
using Azure.Identity;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Hosting.AGUI.AspNetCore;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddAGUIServer();

var projectEndpoint = Environment.GetEnvironmentVariable("FOUNDRY_PROJECT_ENDPOINT")?.TrimEnd('/');
var supportName = Environment.GetEnvironmentVariable("AGENT_SUPPORT");
var researchName = Environment.GetEnvironmentVariable("AGENT_RESEARCH");
var useFoundry = !string.IsNullOrEmpty(projectEndpoint) && !string.IsNullOrEmpty(supportName) && !string.IsNullOrEmpty(researchName);

AIAgent support, research;
if (useFoundry)
{
    // Use the Foundry agents that already exist, through each agent's own endpoint (<project>/agents/<name>/endpoint/protocols/openai).
    // That endpoint serves Hosted Agents and Prompt Agents alike. No new agent is created.
    var project = new AIProjectClient(new Uri(projectEndpoint!), new DefaultAzureCredential());
    AIAgent Agent(string name) => project.AsAIAgent(
        new Uri($"{projectEndpoint}/agents/{Uri.EscapeDataString(name)}/endpoint/protocols/openai"));
    support = Agent(supportName!);
    research = Agent(researchName!);
}
else
{
    support = new ChatClientAgent(new StubChatClient("support"), name: "support");
    research = new ChatClientAgent(new StubChatClient("research"), name: "research");
}

var origins = (Environment.GetEnvironmentVariable("ALLOWED_ORIGINS") ?? "http://localhost:5080")
    .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
builder.Services.AddCors(o => o.AddDefaultPolicy(p => p.WithOrigins(origins).AllowAnyHeader().AllowAnyMethod()));

var app = builder.Build();
app.UseCors();

app.MapGet("/health", () => Results.Ok(new { status = "ok", foundry = useFoundry }));

app.MapAGUIServer("/agui/chat", support);
app.MapAGUIServer("/agui/progress", research);
app.MapAGUIServer("/agui/approval", new ApprovalGateAgent(support));

app.Run();
