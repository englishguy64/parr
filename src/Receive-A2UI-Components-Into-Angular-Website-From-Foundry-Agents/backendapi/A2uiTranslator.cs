using System.Text.Json.Nodes;

/// <summary>
/// A2UI v0.9 message builders, plus the "Responses To A2UI" translator (FromResponse).
/// The "AG-UI To A2UI" translator is in AgUiTranslator.cs and uses the same builders.
///
/// An A2UI surface is built from three kinds of message:
///   createSurface     allocates the surface and names the catalog of components it may use
///   updateComponents  sends the component tree as a flat list: components point at their children by id
///   updateDataModel   sends the data. Components bound to a path, such as {"path": "/answer"}, redraw when it changes
///
/// Because the answer text lives in the data model, a streamed reply only has to send small updateDataModel
/// messages: the component tree is sent once.
/// </summary>
internal static class A2uiTranslator
{
    private const string Version = "v0.9";
    private const string BasicCatalogId = "https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json";

    public static JsonObject CreateSurface(string surfaceId) => new()
    {
        ["version"] = Version,
        ["createSurface"] = new JsonObject { ["surfaceId"] = surfaceId, ["catalogId"] = BasicCatalogId },
    };

    /// <summary>The component tree: Column > Card > Column > heading, agent name, answer, divider, status.</summary>
    public static JsonObject UpdateComponents(string surfaceId, string heading, string agentName) => new()
    {
        ["version"] = Version,
        ["updateComponents"] = new JsonObject
        {
            ["surfaceId"] = surfaceId,
            ["components"] = new JsonArray
            {
                // The component with id "root" is where the renderer starts.
                Component("root", "Column", ("children", new JsonArray("card"))),
                Component("card", "Card", ("child", "body")),
                Component("body", "Column", ("children", new JsonArray("heading", "agent", "answer", "divider", "status"))),
                Component("heading", "Text", ("text", heading), ("variant", "h3")),
                Component("agent", "Text", ("text", $"Foundry agent: {agentName}"), ("variant", "caption")),
                // {"path": "/answer"} binds the text to the data model: change the data and the text redraws.
                Component("answer", "Text", ("text", new JsonObject { ["path"] = "/answer" }), ("variant", "body")),
                Component("divider", "Divider", ("axis", "horizontal")),
                Component("status", "Text", ("text", new JsonObject { ["path"] = "/status" }), ("variant", "caption")),
            },
        },
    };

    /// <summary>Sets the whole data model (path "/").</summary>
    public static JsonObject InitialData(string surfaceId, string answer, string status) =>
        UpdateDataModel(surfaceId, "/", new JsonObject { ["answer"] = answer, ["status"] = status });

    /// <summary>Replaces the value at one path, for example the growing answer text while it streams.</summary>
    public static JsonObject UpdateDataModel(string surfaceId, string path, JsonNode value) => new()
    {
        ["version"] = Version,
        ["updateDataModel"] = new JsonObject { ["surfaceId"] = surfaceId, ["path"] = path, ["value"] = value },
    };

    /// <summary>
    /// "Responses To A2UI" translator: the complete text from the Responses protocol becomes three messages, sent together.
    /// </summary>
    public static JsonArray FromResponse(string surfaceId, string agentName, string answer, string status) => new()
    {
        CreateSurface(surfaceId),
        UpdateComponents(surfaceId, "Answer from the Response agent", agentName),
        InitialData(surfaceId, answer, status),
    };

    private static JsonObject Component(string id, string type, params (string Name, JsonNode Value)[] properties)
    {
        var component = new JsonObject { ["id"] = id, ["component"] = type };
        foreach (var (name, value) in properties) component[name] = value;
        return component;
    }
}
