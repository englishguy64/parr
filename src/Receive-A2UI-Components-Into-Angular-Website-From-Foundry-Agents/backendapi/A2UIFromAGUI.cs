using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json.Nodes;

/// <summary>
/// The "A2UI From AG-UI" translator: turns the AG-UI events a Foundry agent streams into A2UI messages for the website.
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
internal static class A2UIFromAGUI
{
    public static async IAsyncEnumerable<JsonObject> TranslateAsync(
        string surfaceId, string agentName, IAsyncEnumerable<JsonObject> aguiEvents,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        yield return A2UIMessages.CreateSurface(surfaceId);
        yield return A2UIMessages.UpdateComponents(surfaceId, "Streamed answer from the Streaming agent", agentName);
        yield return A2UIMessages.InitialData(surfaceId, "", "Streaming...");

        var timer = Stopwatch.StartNew();
        var text = new StringBuilder();
        string? error = null;

        await foreach (var aguiEvent in aguiEvents.WithCancellation(ct))
        {
            var type = aguiEvent["type"]?.GetValue<string>();
            if (type is "TEXT_MESSAGE_CONTENT" or "TEXT_MESSAGE_CHUNK")
            {
                var delta = aguiEvent["delta"]?.GetValue<string>();
                if (string.IsNullOrEmpty(delta)) continue;
                text.Append(delta);
                // A2UI has no "append": send the whole text so far. The Text component bound to /answer redraws.
                yield return A2UIMessages.UpdateDataModel(surfaceId, "/answer", text.ToString());
            }
            else if (type == "RUN_ERROR")
            {
                error = aguiEvent["message"]?.GetValue<string>() ?? "The agent reported an error";
                break;
            }
            else if (type == "RUN_FINISHED")
            {
                break;
            }
        }

        timer.Stop();
        yield return A2UIMessages.UpdateDataModel(surfaceId, "/status",
            error is null ? $"Complete in {timer.Elapsed.TotalSeconds:0.0} s" : $"Error: {error}");
    }
}
