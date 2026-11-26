// a2ui-response: a Foundry Hosted Agent that RETURNS ITS DATA VIA THE RESPONSES PROTOCOL. The Backend API calls it for
// POST /api/a2ui/response and turns the one complete text answer into A2UI messages (the A2UIFromResponse translator).
//
// Hosted Agents are your own code running in Foundry Agent Service. This one deploys from source (no container, no registry):
// the scripts in ../../azure zip this folder and Foundry runs `dotnet restore` and `dotnet publish`.
//
// Foundry calls the Responses protocol on port 8088, which AddFoundryResponses / MapFoundryResponses provide, including the
// GET /readiness health probe. The agent itself talks to a chat model in the same Foundry project, signing in with the
// platform's identity (DefaultAzureCredential).
//
// Settings:
//   FOUNDRY_PROJECT_ENDPOINT          set by the platform when deployed. Locally: https://<foundry>.services.ai.azure.com/api/projects/<project>
//   AZURE_AI_MODEL_DEPLOYMENT_NAME    chat model deployment to use (default gpt-4.1-mini). Set by the deployment script
//
// Run it on your PC (uses your `az login`, needs the Azure AI User role): dotnet run, then POST http://localhost:8088/responses
using Azure.AI.Projects;
using Azure.Identity;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Foundry.Hosting;

var projectEndpoint = new Uri(
    Environment.GetEnvironmentVariable("FOUNDRY_PROJECT_ENDPOINT")
    ?? throw new InvalidOperationException("FOUNDRY_PROJECT_ENDPOINT is not set."));
var deployment = Environment.GetEnvironmentVariable("AZURE_AI_MODEL_DEPLOYMENT_NAME") ?? "gpt-4.1-mini";

// Plain text only: the Backend API decides how it looks on screen by turning the text into A2UI components.
AIAgent agent = new AIProjectClient(projectEndpoint, new DefaultAzureCredential())
    .AsAIAgent(
        model: deployment,
        instructions: "You are a calm, concise English assistant. Answer in plain text only, with no Markdown, in at most four short sentences.",
        name: "a2ui-response",
        description: "Answers a question with one complete plain text answer.");

var builder = WebApplication.CreateBuilder(args);

// Foundry checks /readiness and calls /responses on port 8088. A container image sets the port in its Dockerfile; deploying
// from source has none, so listen on it here. Without it the readiness check never succeeds and Foundry reports "session_not_ready".
builder.WebHost.UseUrls($"http://0.0.0.0:{Environment.GetEnvironmentVariable("PORT") ?? "8088"}");

// Register on the host builder, not on builder.Services. In a hosted Foundry environment the response-storage settings must bind
// from one configuration section, and the IServiceCollection overload throws at startup.
builder.AddFoundryResponses(agent);

var app = builder.Build();
app.MapFoundryResponses();
app.Run();
