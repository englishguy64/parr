using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json.Nodes;
using Azure.Core;

/// <summary>
/// Calls a Foundry hosted agent that returns data via the AG-UI protocol and yields the AG-UI events it sends.
///
/// AG-UI is a streaming protocol: the caller POSTs a run request and the agent answers with Server-Sent Events (SSE),
/// one event per "data:" line. The events used here are:
///   RUN_STARTED                  the run began
///   TEXT_MESSAGE_START           an assistant message begins
///   TEXT_MESSAGE_CONTENT         one piece (delta) of the text
///   TEXT_MESSAGE_END             the message is complete
///   RUN_FINISHED / RUN_ERROR     the run ended
/// </summary>
internal static class AGUIClient
{
    /// <summary>The address of a hosted agent's Invocations endpoint in a Foundry project.</summary>
    public static string FoundryUrl(string projectEndpoint, string agentName) =>
        $"{projectEndpoint}/agents/{Uri.EscapeDataString(agentName)}/endpoint/protocols/invocations?api-version=v1";

    /// <summary>
    /// Posts an AG-UI run to the hosted agent's Invocations endpoint and reads its event stream.
    /// A hosted agent has to be built to answer this way: it serves AG-UI itself over the Invocations protocol.
    /// A prompt agent cannot, it only speaks the Responses protocol.
    /// </summary>
    public static async IAsyncEnumerable<JsonObject> ReadAsync(
        HttpClient http, TokenCredential? credential, string url, string prompt,
        [EnumeratorCancellation] CancellationToken ct)
    {
        // The AG-UI run request: who is talking (thread, run) and what was said.
        var body = new JsonObject
        {
            ["threadId"] = $"thread_{Guid.NewGuid():N}",
            ["runId"] = $"run_{Guid.NewGuid():N}",
            ["state"] = new JsonObject(),
            ["messages"] = new JsonArray(new JsonObject
            {
                ["id"] = $"msg_{Guid.NewGuid():N}",
                ["role"] = "user",
                ["content"] = prompt,
            }),
            ["tools"] = new JsonArray(),
            ["context"] = new JsonArray(),
            ["forwardedProps"] = new JsonObject(),
        };

        using var request = new HttpRequestMessage(HttpMethod.Post, url)
        {
            Content = new StringContent(body.ToJsonString(), Encoding.UTF8, "application/json"),
        };
        if (credential is not null)   // Foundry needs a Microsoft Entra token. A local agent (no credential) does not
        {
            var token = await credential.GetTokenAsync(new TokenRequestContext(["https://ai.azure.com/.default"]), ct);
            request.Headers.Authorization = new("Bearer", token.Token);
        }
        request.Headers.Accept.Add(new("text/event-stream"));

        // ResponseHeadersRead: start reading as soon as the headers arrive, do not wait for the whole stream.
        using var response = await http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, ct);
        if (!response.IsSuccessStatusCode)
            throw new HttpRequestException($"The AG-UI agent answered {(int)response.StatusCode}: {await response.Content.ReadAsStringAsync(ct)}");

        await using var stream = await response.Content.ReadAsStreamAsync(ct);
        using var reader = new StreamReader(stream);
        while (await reader.ReadLineAsync(ct) is { } line)
        {
            if (!line.StartsWith("data:", StringComparison.Ordinal)) continue;   // skip blank lines and comments
            var json = line[5..].Trim();
            if (json.Length > 0 && JsonNode.Parse(json) is JsonObject aguiEvent) yield return aguiEvent;
        }
    }

    /// <summary>
    /// Stands in for the Foundry agent when FOUNDRY_PROJECT_ENDPOINT is not set. It produces the same AG-UI events a real
    /// agent would, word by word, so the A2UIFromAGUI translator can be tried on a PC without Azure.
    /// </summary>
    public static async IAsyncEnumerable<JsonObject> Stub(string prompt, [EnumeratorCancellation] CancellationToken ct)
    {
        var runId = $"run_{Guid.NewGuid():N}";
        var messageId = $"msg_{Guid.NewGuid():N}";
        var text = $"(Stub AG-UI agent: FOUNDRY_PROJECT_ENDPOINT is not set, so no Foundry agent was called.) You asked: {prompt}";

        yield return new JsonObject { ["type"] = "RUN_STARTED", ["threadId"] = "thread_stub", ["runId"] = runId };
        yield return new JsonObject { ["type"] = "TEXT_MESSAGE_START", ["messageId"] = messageId, ["role"] = "assistant" };
        foreach (var word in text.Split(' '))
        {
            await Task.Delay(80, ct);
            yield return new JsonObject { ["type"] = "TEXT_MESSAGE_CONTENT", ["messageId"] = messageId, ["delta"] = word + " " };
        }
        yield return new JsonObject { ["type"] = "TEXT_MESSAGE_END", ["messageId"] = messageId };
        yield return new JsonObject { ["type"] = "RUN_FINISHED", ["threadId"] = "thread_stub", ["runId"] = runId };
    }
}
