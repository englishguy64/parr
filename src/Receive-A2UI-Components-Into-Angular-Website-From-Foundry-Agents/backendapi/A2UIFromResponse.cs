using System.Text.Json.Nodes;

/// <summary>
/// The "A2UI From Response" translator: the complete text an agent returns via the Responses protocol becomes A2UI messages.
///
///   Responses protocol (from the agent)   A2UI messages (to the website), sent together as one JSON array
///   -----------------------------------   ------------------------------------------------------------------
///   one complete text answer              createSurface, updateComponents, updateDataModel on "/"
///
/// The streamed counterpart, for an agent that returns AG-UI events, is A2UIFromAGUI.
/// </summary>
internal static class A2UIFromResponse
{
    public static JsonArray Translate(string surfaceId, string agentName, string answer, string status) => new()
    {
        A2UIMessages.CreateSurface(surfaceId),
        A2UIMessages.UpdateComponents(surfaceId, "Answer from the Response agent", agentName),
        A2UIMessages.InitialData(surfaceId, answer, status),
    };
}
