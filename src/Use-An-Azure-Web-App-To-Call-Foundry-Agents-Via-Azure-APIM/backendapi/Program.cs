// Backend API: a small REST service that sends a user's message to one of the Foundry agents and returns the reply.
//
// It sits behind API Management. The website posts to APIM, APIM forwards POST /chat here, and this service calls the
// Foundry project's Responses endpoint with its own managed identity (Azure AI User role on the Foundry resource).
//
//   POST /chat        form data: agent (support | research | orchestrator | order-lookup), message
//                     -> 202 {"jobId":"...","status":"running"} + Location: /chat/{jobId}   the answer is not ready: poll
//                     -> 200 {"status":"done","reply":"..."}   Foundry had already finished (final answer, no polling)
//                     -> 400 bad request   500 not configured   502 Foundry call failed
//   GET  /chat/{jobId} -> 200 {"status":"running"} | {"status":"done","reply":"..."} | {"status":"failed","error":"..."}
//                         404 unknown or expired job   400 invalid id   502 Foundry call failed
//   GET  /health      -> 200
//
// Long-running calls: POST starts the Foundry call in background mode and returns Foundry's response id as the job
// id; each GET does one lookup of that response. This service holds no job state, so restarts and scale-out are safe.
//
// Settings (App Service application settings, set by create_backendapi.bicep, or environment variables locally):
//   FOUNDRY_PROJECT_ENDPOINT   https://<foundry>.services.ai.azure.com/api/projects/<project>
//   AGENT_SUPPORT              Foundry agent name that answers "support"
//   AGENT_RESEARCH             Foundry agent name that answers "research"
//   AGENT_ORCHESTRATOR         Foundry agent name that answers "orchestrator"
//   AGENT_ORDER_LOOKUP         Foundry agent name that answers "order-lookup"
//   SAMPLE_RECEIPT_URL         https address of the sample receipt in Blob Storage (put there by create_samplereceipt.bicep).
//                              When a message to Order Lookup or the orchestrator mentions a receipt, this address is added
//                              to it. Order Lookup downloads the file itself with its own Entra identity: this service never
//                              touches the file, and the address opens nothing without a role on the storage account.
//
// Locally it signs in with your `az login` (DefaultAzureCredential). Your user needs the Azure AI User role, and
// Foundry must still allow public access (or run this from inside the VNet).
//
// The Foundry REST shape used below (/openai/v1/responses with an agent_reference) follows the preview API, the same
// one the orchestrator Hosted Agent uses: check it against the current Foundry documentation before relying on it.
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Azure.Core;
using Azure.Identity;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<TokenCredential>(new DefaultAzureCredential());
builder.Services.AddHttpClient("foundry", c => c.Timeout = TimeSpan.FromMinutes(2));
var app = builder.Build();

var projectEndpoint = Environment.GetEnvironmentVariable("FOUNDRY_PROJECT_ENDPOINT")?.TrimEnd('/');
var sampleReceiptUrl = Environment.GetEnvironmentVariable("SAMPLE_RECEIPT_URL");

// Public agent id (what the website sends) -> Foundry agent name.
var agents = new Dictionary<string, string?>
{
    ["support"] = Environment.GetEnvironmentVariable("AGENT_SUPPORT"),
    ["research"] = Environment.GetEnvironmentVariable("AGENT_RESEARCH"),
    ["orchestrator"] = Environment.GetEnvironmentVariable("AGENT_ORCHESTRATOR"),
    ["order-lookup"] = Environment.GetEnvironmentVariable("AGENT_ORDER_LOOKUP"),
};

app.MapGet("/health", () => Results.Ok(new { status = "ok", configured = !string.IsNullOrEmpty(projectEndpoint) }));

app.MapPost("/chat", async (HttpRequest request, TokenCredential credential, IHttpClientFactory clients) =>
{
    if (!request.HasFormContentType) return Results.BadRequest(new { error = "Send multipart/form-data." });
    var form = await request.ReadFormAsync();
    var agent = form["agent"].ToString();
    var message = form["message"].ToString();

    if (!agents.TryGetValue(agent, out var foundryAgent))
        return Results.BadRequest(new { error = $"Unknown agent '{agent}'. Use one of: {string.Join(", ", agents.Keys)}." });
    if (string.IsNullOrWhiteSpace(message))
        return Results.BadRequest(new { error = "Enter a message." });
    if (string.IsNullOrEmpty(projectEndpoint) || string.IsNullOrEmpty(foundryAgent))
        return Results.Json(new { error = $"The service is not configured for agent '{agent}' (FOUNDRY_PROJECT_ENDPOINT or AGENT_* setting missing)." }, statusCode: 500);

    var input = WithSampleReceipt(message, agent, sampleReceiptUrl);

    // background + store: Foundry accepts the request, answers at once with a response id and status "queued", and
    // keeps the response so it can be read back later. That id is the job id: this service keeps no state of its own.
    // Hosted Agents (orchestrator, order-lookup) can only be called through their own agent endpoint, and they answer in
    // the same request, so there is nothing to poll: the reply comes back as a 200 below. The Prompt Agents use the
    // project's Responses endpoint with an agent_reference ("agent" is deprecated: Foundry answers 400).
    var hosted = agent is "orchestrator" or "order-lookup";
    var body = hosted
        ? new JsonObject { ["input"] = input }
        : new JsonObject
        {
            ["agent_reference"] = new JsonObject { ["type"] = "agent_reference", ["name"] = foundryAgent },
            ["input"] = input,
            ["background"] = true,
            ["store"] = true,
        };
    var callUrl = hosted
        ? $"{projectEndpoint}/agents/{Uri.EscapeDataString(foundryAgent)}/endpoint/protocols/openai/responses?api-version=v1"
        : $"{projectEndpoint}/openai/v1/responses";

    try
    {
        var token = await credential.GetTokenAsync(new TokenRequestContext(["https://ai.azure.com/.default"]), default);
        using var call = new HttpRequestMessage(HttpMethod.Post, callUrl)
        {
            Content = new StringContent(body.ToJsonString(), Encoding.UTF8, "application/json"),
        };
        call.Headers.Authorization = new("Bearer", token.Token);

        using var response = await clients.CreateClient("foundry").SendAsync(call);
        var text = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
            return Results.Json(new { error = $"Foundry returned {(int)response.StatusCode}.", detail = text }, statusCode: 502);

        var job = ReadJob(text);

        // Still working: 202 with the job id. The caller polls GET /chat/{jobId}.
        if (job.Status == "running" && job.Id is not null)
        {
            request.HttpContext.Response.Headers.Location = $"/chat/{job.Id}";
            return Results.Json(new { jobId = job.Id, status = "running", agent }, statusCode: StatusCodes.Status202Accepted);
        }

        // Already finished (or failed) on the first call, for example a Hosted Agent that answers straight away:
        // return the result now. The caller treats a 200 as the final answer.
        return Results.Json(new { jobId = job.Id, status = job.Status, agent, reply = job.Reply, error = job.Error });
    }
    catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or AuthenticationFailedException)
    {
        return Results.Json(new { error = $"Could not call Foundry: {ex.Message}" }, statusCode: 502);
    }
});

// Poll for the result. One lookup per call: the job id is Foundry's response id, so Foundry holds the state.
//   200 {"jobId","status":"running"}                       still working, ask again shortly
//   200 {"jobId","status":"done","reply":"..."}            finished
//   200 {"jobId","status":"failed","error":"..."}          the agent run failed or was cancelled
//   400 bad id   404 unknown or expired job   502 Foundry call failed
app.MapGet("/chat/{jobId}", async (string jobId, HttpRequest http, TokenCredential credential, IHttpClientFactory clients) =>
{
    // Foundry response ids look like resp_<letters and digits>. Reject anything else so the value can't alter the URL.
    if (!Regex.IsMatch(jobId, "^[A-Za-z0-9_-]{8,128}$")) return Results.BadRequest(new { error = "Invalid job id." });
    if (string.IsNullOrEmpty(projectEndpoint))
        return Results.Json(new { error = "The service is not configured (FOUNDRY_PROJECT_ENDPOINT missing)." }, statusCode: 500);

    try
    {
        var token = await credential.GetTokenAsync(new TokenRequestContext(["https://ai.azure.com/.default"]), default);
        using var call = new HttpRequestMessage(HttpMethod.Get, $"{projectEndpoint}/openai/v1/responses/{Uri.EscapeDataString(jobId)}");
        call.Headers.Authorization = new("Bearer", token.Token);

        using var response = await clients.CreateClient("foundry").SendAsync(call);
        var text = await response.Content.ReadAsStringAsync();
        if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
            return Results.NotFound(new { error = "Unknown or expired job." });
        if (!response.IsSuccessStatusCode)
            return Results.Json(new { error = $"Foundry returned {(int)response.StatusCode}.", detail = text }, statusCode: 502);

        var job = ReadJob(text);
        if (job.Status == "running") http.HttpContext.Response.Headers["Retry-After"] = "2";   // a hint for pollers
        return Results.Json(new { jobId, status = job.Status, reply = job.Reply, error = job.Error });
    }
    catch (Exception ex) when (ex is HttpRequestException or TaskCanceledException or AuthenticationFailedException)
    {
        return Results.Json(new { error = $"Could not call Foundry: {ex.Message}" }, statusCode: 502);
    }
});

app.Run();

// ---------------------------------------------------------------------------------------------

// When the message mentions a receipt and the user is talking to Order Lookup or the orchestrator, add the address of the
// sample receipt, last and on its own line. Order Lookup finds the https address in the text, downloads the file with its
// own Entra identity and reads it with Document Intelligence. The address opens nothing by itself: the storage account only
// accepts Entra ID sign-ins. The Prompt Agents (support, research) can't read private storage, so they are left alone, and
// a message that already contains its own https link is not changed.
static JsonNode WithSampleReceipt(string message, string agent, string? sampleReceiptUrl)
{
    var wantsReceipt = agent is "order-lookup" or "orchestrator"
        && !string.IsNullOrEmpty(sampleReceiptUrl)
        && Regex.IsMatch(message, @"\breceipts?\b", RegexOptions.IgnoreCase)
        && !message.Contains("https://", StringComparison.OrdinalIgnoreCase);

    return JsonValue.Create(wantsReceipt
        ? $"{message}\n\nAttachment (sample-receipt.png): {sampleReceiptUrl}"
        : message)!;
}
// Reads a Foundry Responses payload and maps its status to one of three: running, done, failed.
//   queued, in_progress                  -> running
//   completed (or no status: a plain reply) -> done, with the assistant text from "output"
//   failed, cancelled, incomplete        -> failed, with the error message if there is one
// A 200 from Foundry only means the call worked: the status in the body says whether the answer is ready.
static (string? Id, string Status, string? Reply, string? Error) ReadJob(string json)
{
    var node = JsonNode.Parse(json);
    var id = node?["id"]?.GetValue<string>();
    var raw = node?["status"]?.GetValue<string>() ?? "completed";

    var sb = new StringBuilder();
    foreach (var item in node?["output"]?.AsArray() ?? [])
        foreach (var part in item?["content"]?.AsArray() ?? [])
            if (part?["text"] is JsonNode t) sb.Append(t.GetValue<string>());
    var reply = sb.Length > 0 ? sb.ToString() : null;

    var status = raw switch
    {
        "queued" or "in_progress" => "running",
        "completed" => "done",
        "failed" or "cancelled" or "incomplete" => "failed",
        _ => reply is not null ? "done" : "running",
    };

    string? error = null;
    if (status == "failed")
        error = node?["error"]?["message"]?.GetValue<string>()
            ?? node?["incomplete_details"]?["reason"]?.GetValue<string>()
            ?? $"The agent run ended with status '{raw}'.";

    // A finished response with no text still has to show something.
    if (status == "done" && reply is null) reply = json;
    return (id, status, reply, error);
}
