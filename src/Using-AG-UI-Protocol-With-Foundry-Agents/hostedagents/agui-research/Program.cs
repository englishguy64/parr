// agui-research: a Foundry Hosted Agent that does a longer piece of work. The Backend reaches it for the "Show live agent
// progress" use case: it is an English tutor, so each answer is several corrections with an explanation, which gives the
// page something to show while the run is in progress.
//
// It deploys from source in the same way as agui-support: see the README in the hostedagents folder.
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
        instructions: "You are an English tutor. Correct the user's grammar, list each fix on its own line, and briefly explain why.",
        name: "agui-research",
        description: "Corrects grammar and explains each fix.");

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
