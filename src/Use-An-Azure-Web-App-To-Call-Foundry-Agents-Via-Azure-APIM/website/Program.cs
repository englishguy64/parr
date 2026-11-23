// Website for the Foundry agents. It only serves the page and tells the page where to go:
//
//   Browser --(Entra sign-in with MSAL.js)--> Entra ID
//   Browser --(Bearer access token)-------> API Management --(policies: CORS, token check, rate limit)--> Backend API --> Foundry
//
// The browser signs the user in and calls APIM directly, so this app never sees the user's token and forwards nothing.
// Long-running agents: POST {APIM}/chat answers 202 {"jobId":...} (or 200 with the reply if it was quick), and the page
// polls GET {APIM}/chat/{jobId} until the status is "done" or "failed".
//
// Settings (App Service application settings, or environment variables locally). None is a secret:
//   APIM_BASE_URL     for example https://<TENANT_PREFIX>-apim.azure-api.net/api
//                     (leave empty to run the page locally: a fake /api/chat in this app answers, nothing is sent)
//   ENTRA_TENANT_ID   Entra tenant id
//   ENTRA_CLIENT_ID   app registration (client) id from 10_create-entraapp.ps1; leave empty to turn sign-in off
//
// The app registration needs these redirect URIs (Single-page application platform), which the script sets:
//   https://<web app name>.azurewebsites.net/    (deployed)
//   http://localhost:5080/                       (local)
using System.Collections.Concurrent;
using System.Text.RegularExpressions;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.UseDefaultFiles();
app.UseStaticFiles();

var apimBase = Environment.GetEnvironmentVariable("APIM_BASE_URL")?.TrimEnd('/');
var tenantId = Environment.GetEnvironmentVariable("ENTRA_TENANT_ID");
var clientId = Environment.GetEnvironmentVariable("ENTRA_CLIENT_ID");

// What the page needs to start MSAL and find APIM. No secrets: a browser can't keep one.
app.MapGet("/config.json", () => Results.Json(new
{
    apimBaseUrl = apimBase,
    tenantId,
    clientId,
}));

// ---------- local stand-in for APIM ----------
// Only used when APIM_BASE_URL is empty, so the page's sign-in-free flow, waiting and polling can be tried on a PC
// without Azure. The page then calls /api/chat on this app instead of APIM.
var localJobs = new ConcurrentDictionary<string, (DateTime Started, string Reply)>();
string[] knownAgents = ["support", "research", "orchestrator", "order-lookup"];

app.MapPost("/api/chat", async (HttpRequest request) =>
{
    if (!string.IsNullOrEmpty(apimBase)) return Results.NotFound();   // not a local run: the page talks to APIM
    if (!request.HasFormContentType) return Results.BadRequest(new { error = "Send a form." });
    var form = await request.ReadFormAsync();
    var agent = form["agent"].ToString();
    var message = form["message"].ToString();

    if (!knownAgents.Contains(agent)) return Results.BadRequest(new { error = "Unknown agent." });
    if (string.IsNullOrWhiteSpace(message))
        return Results.BadRequest(new { error = "Enter a message." });

    var id = $"local-{Guid.NewGuid():N}";
    localJobs[id] = (DateTime.UtcNow,
        $"(APIM_BASE_URL is not set, so nothing was sent.)\nAgent: {agent}\nMessage: {message}");
    return Results.Json(new { jobId = id, status = "running" }, statusCode: StatusCodes.Status202Accepted);
});

app.MapGet("/api/chat/{jobId}", (string jobId) =>
{
    if (!string.IsNullOrEmpty(apimBase)) return Results.NotFound();
    if (!Regex.IsMatch(jobId, "^[A-Za-z0-9_-]{8,128}$")) return Results.BadRequest(new { error = "Invalid job id." });
    if (!localJobs.TryGetValue(jobId, out var job)) return Results.NotFound(new { error = "Unknown or expired job." });
    return DateTime.UtcNow - job.Started < TimeSpan.FromSeconds(3)
        ? Results.Json(new { jobId, status = "running" })
        : Results.Json(new { jobId, status = "done", reply = job.Reply });
});

app.Run();
