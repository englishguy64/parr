// Backend API: calls two Foundry agents, each over its own protocol, and translates both into A2UI messages for the
// Angular website.
//
//   Agent that returns data via the Responses protocol --> "Responses To A2UI" translator --> website (one JSON array)
//   Agent that returns data via the AG-UI protocol     --> "AG-UI To A2UI" translator     --> website (one message per line)
//
//   POST /api/a2ui/response   {prompt, surfaceId}  calls the RESPONSE agent over the Foundry Responses protocol and waits
//                              for the complete answer. Returns one JSON array of A2UI messages.
//   POST /api/a2ui/stream     {prompt, surfaceId}  calls the STREAMING agent over the AG-UI protocol and translates each
//                              AG-UI event into an A2UI message as it arrives. Returns newline delimited JSON: one A2UI
//                              message per line, flushed as it is produced.
//   GET  /health
//
// The two Foundry agents are hosted agents written in C# (../hostedagents) and deployed by ../azure. Only their names are used here:
//
//   AGENT_RESPONSE   name of the agent that returns data via the Responses protocol   (default: a2ui-response)
//                    Any Prompt Agent or Hosted Agent works.
//   AGENT_STREAM     name of the agent that returns data via the AG-UI protocol       (default: a2ui-stream)
//                    A Hosted Agent that serves AG-UI over the Invocations protocol (../hostedagents/a2ui-stream).
//
// Settings (App Service application settings, or environment variables locally):
//   FOUNDRY_PROJECT_ENDPOINT   https://<foundry>.services.ai.azure.com/api/projects/<project>
//                              (empty: run with stubs that return a canned answer, nothing is sent to Azure)
//   AGENT_RESPONSE, AGENT_STREAM   Foundry agent names, see above
//   AGENT_STREAM_URL           optional: address of an AG-UI agent on your PC, for example http://localhost:8088/invocations.
//                              Replaces the Foundry call for the streaming agent, no sign-in. For local testing only
//   ALLOWED_ORIGINS            comma separated website origins for CORS, default http://localhost:4200
//
// Locally it signs in with your `az login` (DefaultAzureCredential). Your user needs the Azure AI User role on the Foundry
// resource. In App Service, give the app a managed identity with the same role.
//
// The Foundry packages and the Invocations endpoint are preview: check them against the current documentation before
// relying on them.
using System.Diagnostics;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Azure.AI.Projects;
using Azure.Core;
using Azure.Identity;
using Microsoft.Agents.AI;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls(Environment.GetEnvironmentVariable("ASPNETCORE_URLS") ?? "http://localhost:5200");

var projectEndpoint = Environment.GetEnvironmentVariable("FOUNDRY_PROJECT_ENDPOINT")?.TrimEnd('/');
var responseName = Environment.GetEnvironmentVariable("AGENT_RESPONSE") ?? "a2ui-response";
var streamName = Environment.GetEnvironmentVariable("AGENT_STREAM") ?? "a2ui-stream";
var useFoundry = !string.IsNullOrEmpty(projectEndpoint);
// Optional: the address of an AG-UI agent running on your PC, for example http://localhost:8088/invocations (see
// ../hostedagents/README.md). When set it replaces the Foundry call for the streaming agent, and no sign-in is used.
var streamUrl = Environment.GetEnvironmentVariable("AGENT_STREAM_URL");

TokenCredential credential = new DefaultAzureCredential();
builder.Services.AddHttpClient("agui", c => c.Timeout = TimeSpan.FromMinutes(5));

// The Response agent is called over the Foundry Responses protocol, through its own endpoint
// (<project>/agents/<name>/endpoint/protocols/openai). Nothing is created in Foundry.
AIAgent responseAgent = useFoundry
    ? new AIProjectClient(new Uri(projectEndpoint!), credential).AsAIAgent(
        new Uri($"{projectEndpoint}/agents/{Uri.EscapeDataString(responseName)}/endpoint/protocols/openai"))
    : new ChatClientAgent(new StubChatClient("response"), name: "response");

var origins = (Environment.GetEnvironmentVariable("ALLOWED_ORIGINS") ?? "http://localhost:4200")
    .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
builder.Services.AddCors(o => o.AddDefaultPolicy(p => p.WithOrigins(origins).AllowAnyHeader().AllowAnyMethod()));

var app = builder.Build();
app.UseCors();

app.MapGet("/health", () => Results.Ok(new { status = "ok", foundry = useFoundry }));

// ---- Agent 1: Responses protocol, one complete answer ------------------------------------------------------------------
app.MapPost("/api/a2ui/response", async (AskRequest request, CancellationToken ct) =>
{
    if (string.IsNullOrWhiteSpace(request.Prompt)) return Results.BadRequest(new { error = "Enter a question." });
    var surfaceId = SafeSurfaceId(request.SurfaceId);

    var timer = Stopwatch.StartNew();
    var reply = await responseAgent.RunAsync(request.Prompt, cancellationToken: ct);   // Responses protocol, one round trip
    timer.Stop();

    // "Responses To A2UI" translator: plain text in, three A2UI messages out.
    var messages = A2uiTranslator.FromResponse(surfaceId, responseName, reply.Text,
        $"Complete in {timer.Elapsed.TotalSeconds:0.0} s");
    return Results.Json(messages);
});

// ---- Agent 2: AG-UI protocol, streamed ---------------------------------------------------------------------------------
app.MapPost("/api/a2ui/stream", async (AskRequest request, HttpResponse response, IHttpClientFactory clients, CancellationToken ct) =>
{
    if (string.IsNullOrWhiteSpace(request.Prompt))
    {
        response.StatusCode = StatusCodes.Status400BadRequest;
        await response.WriteAsJsonAsync(new { error = "Enter a question." }, ct);
        return;
    }
    var surfaceId = SafeSurfaceId(request.SurfaceId);

    // One A2UI message per line. Flush after each so the website can render it at once.
    response.ContentType = "application/x-ndjson";
    response.Headers.CacheControl = "no-store";
    async Task Send(JsonObject message)
    {
        await response.WriteAsync(message.ToJsonString() + "\n", ct);
        await response.Body.FlushAsync(ct);
    }

    // AG-UI events in from the agent (or from the stub), A2UI messages out to the website.
    var http = clients.CreateClient("agui");
    var agUiEvents =
        !string.IsNullOrEmpty(streamUrl)                      // a local AG-UI agent: no sign-in needed
            ? AgUiClient.ReadAsync(http, null, streamUrl, request.Prompt, ct)
        : useFoundry                                          // the hosted agent in Foundry
            ? AgUiClient.ReadAsync(http, credential, AgUiClient.FoundryUrl(projectEndpoint!, streamName), request.Prompt, ct)
            : AgUiClient.Stub(request.Prompt, ct);            // nothing configured: canned events

    try
    {
        await foreach (var message in AgUiTranslator.TranslateAsync(surfaceId, streamName, agUiEvents, ct))
            await Send(message);
    }
    catch (Exception e) when (e is not OperationCanceledException)
    {
        // The stream has started, so the status code can no longer change: report the error on the card instead.
        await Send(A2uiTranslator.UpdateDataModel(surfaceId, "/status", $"Error: {e.Message}"));
    }
});

app.Run();

// Surface ids come from the browser, so keep only safe characters.
static string SafeSurfaceId(string? id) =>
    !string.IsNullOrEmpty(id) && Regex.IsMatch(id, "^[A-Za-z0-9_-]{1,40}$") ? id : $"answer-{Guid.NewGuid():N}";

internal sealed record AskRequest(string? Prompt, string? SurfaceId);
