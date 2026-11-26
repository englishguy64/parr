using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json.Nodes;

/// <summary>
/// The "AG-UI To A2UI" translator: turns the AG-UI events a Foundry agent streams into A2UI messages for the website.
///
///   AG-UI event (from the agent)         A2UI message (to the website)
///   ----------------------------         -----------------------------
///   (start of the run)                   createSurface, updateComponents, updateDataModel "/"
///   TEXT_MESSAGE_CONTENT {delta}         updateDataModel "/answer" with the text so far
///   RUN_FINISHED                         updateDataModel "/status": complete
///   RUN_ERROR                            updateDataModel "/status": the error
///
/// The surface and its components are sent once, at the start. After that only the data changes, so each message is tiny.
/// </summary>
internal static class AgUiTranslator
{
    public static async IAsyncEnumerable<JsonObject> TranslateAsync(
        string surfaceId, string agentName, IAsyncEnumerable<JsonObject> agUiEvents,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        yield return A2uiTranslator.CreateSurface(surfaceId);
        yield return A2uiTranslator.UpdateComponents(surfaceId, "Streamed answer from the Streaming agent", agentName);
        yield return A2uiTranslator.InitialData(surfaceId, "", "Streaming...");

        var timer = Stopwatch.StartNew();
        var text = new StringBuilder();
        string? error = null;

        await foreach (var agUiEvent in agUiEvents.WithCancellation(ct))
        {
            var type = agUiEvent["type"]?.GetValue<string>();
            if (type is "TEXT_MESSAGE_CONTENT" or "TEXT_MESSAGE_CHUNK")
            {
                var delta = agUiEvent["delta"]?.GetValue<string>();
                if (string.IsNullOrEmpty(delta)) continue;
                text.Append(delta);
                // A2UI has no "append": send the whole text so far. The Text component bound to /answer redraws.
                yield return A2uiTranslator.UpdateDataModel(surfaceId, "/answer", text.ToString());
            }
            else if (type == "RUN_ERROR")
            {
                error = agUiEvent["message"]?.GetValue<string>() ?? "The agent reported an error";
                break;
            }
            else if (type == "RUN_FINISHED")
            {
                break;
            }
        }

        timer.Stop();
        yield return A2uiTranslator.UpdateDataModel(surfaceId, "/status",
            error is null ? $"Complete in {timer.Elapsed.TotalSeconds:0.0} s" : $"Error: {error}");
    }
}
