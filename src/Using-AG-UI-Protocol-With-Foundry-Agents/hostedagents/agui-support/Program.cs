// agui-support: a Foundry Hosted Agent that answers support questions. The Backend reaches it for the "Stream a chat answer"
// and "Approve before an action" use cases.
//
// Hosted Agents are your own code running in Foundry Agent Service. This one deploys from source (no container, no registry):
// the Foundry Toolkit for VS Code zips this folder and Foundry runs `dotnet restore` and `dotnet publish`.
//
// Foundry calls the Responses protocol on port 8088, which AddFoundryResponses / MapFoundryResponses provide. The agent itself
// talks to a chat model in the same Foundry project, signing in with the platform's identity (DefaultAzureCredential).
//
// Settings:
//   FOUNDRY_PROJECT_ENDPOINT          set by the platform when deployed. Locally: https://<foundry>.services.ai.azure.com/api/projects/<project>
//   AZURE_AI_MODEL_DEPLOYMENT_NAME    chat model deployment to use (default gpt-4.1-mini). Set it in azure.yaml (env)
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

AIAgent agent = new AIProjectClient(projectEndpoint, new DefaultAzureCredential())
    .AsAIAgent(
        model: deployment,
        instructions: "You are a concise, friendly English assistant for customer support. Answer in at most three sentences.",
        name: "agui-support",
        description: "Answers customer support questions briefly.");

var builder = WebApplication.CreateBuilder(args);

// Foundry checks /readiness and calls /responses on port 8088 (the platform sets PORT=8088). A container image sets this in its
// Dockerfile; deploying from source has none, so listen on that port here. Without it the app listens on its default port,
// the readiness check never succeeds and Foundry reports "session_not_ready".
builder.WebHost.UseUrls($"http://0.0.0.0:{Environment.GetEnvironmentVariable("PORT") ?? "8088"}");

// Register on the host builder, not on builder.Services. In a hosted Foundry environment the response-storage settings must bind
// from one configuration section, and the IServiceCollection overload throws at startup ("cannot be used in a hosted Foundry
// environment"), so the agent never becomes ready and calls fail with 424 session_not_ready.
builder.AddFoundryResponses(agent);

var app = builder.Build();
app.MapFoundryResponses();
app.Run();
