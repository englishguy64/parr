// Orchestrator Hosted Agent: plans the steps for a request, delegates them to the other agents, and combines the results.
//
// Runs as a container in Foundry Agent Service. Foundry calls POST /responses on port 8088.
// Environment (the service sets the project identity; you set the rest in the agent definition):
//   FOUNDRY_PROJECT_ENDPOINT   https://<foundry>.services.ai.azure.com/api/projects/<project>
//   FOUNDRY_MODEL_DEPLOYMENT   chat model deployment used for planning and for the final answer
//   CUSTOM_AGENTS              comma separated names of the agents it may delegate to
//                              (set by create_foundryhostedagents.bicep)
//
// The Foundry REST shapes used below (/openai/v1/responses for the model, and each Hosted Agent's own
// /agents/<name>/endpoint/protocols/openai/responses endpoint) follow the preview API:
// check them against the current Foundry documentation before relying on this.
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Azure.Core;
using Azure.Identity;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<TokenCredential>(new DefaultAzureCredential());
builder.Services.AddHttpClient();
var app = builder.Build();

var projectEndpoint = Environment.GetEnvironmentVariable("FOUNDRY_PROJECT_ENDPOINT")
    ?? throw new InvalidOperationException("Set FOUNDRY_PROJECT_ENDPOINT");
var model = Environment.GetEnvironmentVariable("FOUNDRY_MODEL_DEPLOYMENT") ?? "gpt-4.1-mini";
var agentNames = (Environment.GetEnvironmentVariable("CUSTOM_AGENTS") ?? "")
    .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

app.MapGet("/readiness", () => Results.Ok());

app.MapPost("/responses", async (JsonNode request, TokenCredential credential, IHttpClientFactory http) =>
{
    var userText = ExtractText(request["input"]);
    var foundry = new Foundry(http.CreateClient(), credential, projectEndpoint);

    // 1. PLAN: ask the model which agents are needed and what to ask each one.
    var planPrompt =
        "You coordinate specialist agents for a customer support case. " +
        $"Available agents: {string.Join(", ", agentNames)}. " +
        "Agents named *order-lookup find order status and details. Agents named *policy-check apply the return and refund policy. " +
        "Reply with JSON only: {\"steps\":[{\"agent\":\"<exact agent name>\",\"input\":\"<question for that agent>\"}]}. " +
        "If the request contains an https link to an attached file (a receipt or invoice), copy that link exactly, unchanged, into the input for the order-lookup agent. " +
        "Use only the agents that are needed.";
    var planJson = await foundry.AskModelAsync(model, planPrompt, userText);
    var steps = ParsePlan(planJson, agentNames);

    // 2. DELEGATE: call the chosen agents in parallel.
    // The attached-file link (a temporary Blob Storage link added by the Backend API) must reach Order Lookup intact,
    // which reads it with Document Intelligence. The model may drop or reword it, so put it back if it is missing.
    var attachment = System.Text.RegularExpressions.Regex.Match(userText, @"https://\S+").Value;
    string WithAttachment(string agent, string input) =>
        attachment.Length > 0 && agent.EndsWith("order-lookup") && !input.Contains(attachment)
            ? $"{input}\n{attachment}"
            : input;

    var results = await Task.WhenAll(steps.Select(async s =>
        (s.Agent, Answer: await foundry.AskAgentAsync(s.Agent, WithAttachment(s.Agent, s.Input)))));

    // 3. COMBINE: write one answer from the agents' results.
    var combinePrompt =
        "Write a short, clear reply to the customer using only the agent results below. " +
        "If an agent failed, say what could not be checked.\n" +
        string.Join("\n", results.Select(r => $"[{r.Agent}] {r.Answer}"));
    var answer = await foundry.AskModelAsync(model, combinePrompt, userText);

    return Results.Json(ResponseBody(answer));
});

app.Run();

// ---------------------------------------------------------------------------------------------

static string ExtractText(JsonNode? input)
{
    if (input is JsonValue v && v.TryGetValue<string>(out var s)) return s;
    if (input is JsonArray items)
        return string.Join("\n", items.SelectMany(i => i?["content"] is JsonArray c
            ? c.Select(p => p?["text"]?.GetValue<string>() ?? "")
            : new[] { i?["content"]?.GetValue<string>() ?? "" }));
    return "";
}

static List<(string Agent, string Input)> ParsePlan(string json, string[] allowed)
{
    var steps = new List<(string, string)>();
    try
    {
        var start = json.IndexOf('{');
        var end = json.LastIndexOf('}');
        var plan = JsonNode.Parse(json[start..(end + 1)]);
        foreach (var step in plan?["steps"]?.AsArray() ?? [])
        {
            var agent = step?["agent"]?.GetValue<string>();
            var input = step?["input"]?.GetValue<string>();
            if (agent is not null && input is not null && allowed.Contains(agent)) steps.Add((agent, input));
        }
    }
    catch (Exception) { /* fall through to the default plan */ }
    // Never return an empty plan: ask every agent the original question.
    return steps.Count > 0 ? steps : allowed.Select(a => (a, "Handle this request.")).ToList();
}

static object ResponseBody(string text) => new
{
    id = $"resp_{Guid.NewGuid():N}",
    @object = "response",
    status = "completed",
    output = new[]
    {
        new
        {
            type = "message",
            role = "assistant",
            content = new[] { new { type = "output_text", text } },
        },
    },
};

// Thin client for the Foundry project's Responses endpoint, authenticated with the container's managed identity.
sealed class Foundry(HttpClient client, TokenCredential credential, string projectEndpoint)
{
    public Task<string> AskModelAsync(string model, string instructions, string input) =>
        PostAsync($"{projectEndpoint.TrimEnd('/')}/openai/v1/responses",
            new JsonObject { ["model"] = model, ["instructions"] = instructions, ["input"] = input });

    // The agents it delegates to are Hosted Agents. Foundry only lets them be called through their own agent endpoint
    // (a call to /openai/v1/responses with an agent_reference is rejected), and the endpoint answers in the same request.
    public Task<string> AskAgentAsync(string agentName, string input) =>
        PostAsync($"{projectEndpoint.TrimEnd('/')}/agents/{Uri.EscapeDataString(agentName)}/endpoint/protocols/openai/responses?api-version=v1",
            new JsonObject { ["input"] = input });

    private async Task<string> PostAsync(string url, JsonObject body)
    {
        var token = await credential.GetTokenAsync(new TokenRequestContext(["https://ai.azure.com/.default"]), default);
        using var request = new HttpRequestMessage(HttpMethod.Post, url);
        request.Headers.Authorization = new("Bearer", token.Token);
        request.Content = new StringContent(body.ToJsonString(), Encoding.UTF8, "application/json");
        using var response = await client.SendAsync(request);
        var text = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode) return $"(error {(int)response.StatusCode}: {text})";

        // Pull the assistant text out of the Responses payload.
        var parsed = JsonNode.Parse(text);
        var sb = new StringBuilder();
        foreach (var item in parsed?["output"]?.AsArray() ?? [])
            foreach (var part in item?["content"]?.AsArray() ?? [])
                if (part?["text"] is JsonNode t) sb.Append(t.GetValue<string>());
        return sb.Length > 0 ? sb.ToString() : text;
    }
}
