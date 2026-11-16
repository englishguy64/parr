// Order Lookup Hosted Agent: finds order status and details.
//
// This is the kind of agent that earns a container: it runs your own code (here an in-memory stand-in for an
// order system) rather than just a prompt. Replace the dictionary with a call to your real order API or database.
//
// Runs as a container in Foundry Agent Service. Foundry calls POST /responses on port 8088.
//
// It also shows how to use a Foundry prebuilt service from a Hosted Agent: if the request contains a link to a
// receipt or invoice, the agent reads it with Document Intelligence (the same Foundry resource, Entra ID auth).
//   DOCUMENT_INTELLIGENCE_ENDPOINT   https://<foundry>.cognitiveservices.azure.com/
// The container's identity needs the Cognitive Services User role on the Foundry resource.
//
//
// Try the receipt reading on your PC with the sample image in this folder (uses your `az login`):
//   $env:DOCUMENT_INTELLIGENCE_ENDPOINT = "https://<foundry>.cognitiveservices.azure.com/"
//   dotnet run -- sample-receipt.png                      (a local file: its bytes are sent to the service)
//   dotnet run -- https://example.com/receipt.png         (a web link: the service fetches it)
// With no argument, `dotnet run` starts the agent as usual.
//
// The Policy Check agent follows the same shape: parse the request, apply your rules in code, return the result.
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Azure;
using Azure.AI.DocumentIntelligence;
using Azure.Identity;
using Azure.Storage.Blobs;

var docEndpoint = Environment.GetEnvironmentVariable("DOCUMENT_INTELLIGENCE_ENDPOINT");
var docClient = docEndpoint is null ? null : new DocumentIntelligenceClient(new Uri(docEndpoint), new DefaultAzureCredential());

// Local test mode: `dotnet run -- <local file or https link>` reads the receipt, prints the result and exits.
if (args.Length == 1 && !args[0].StartsWith("--"))
{
    if (!IsWebLink(args[0]) && !File.Exists(args[0]))
    {
        Console.Error.WriteLine($"'{args[0]}' is not an https link or an existing file.");
        return 1;
    }
    if (docClient is null)
    {
        Console.Error.WriteLine("Set DOCUMENT_INTELLIGENCE_ENDPOINT first, for example https://<foundry>.cognitiveservices.azure.com/");
        return 1;
    }
    Console.WriteLine(await ReadReceiptAsync(docClient, await ReceiptOptionsAsync(args[0])));
    return 0;
}

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// Stand-in order data. Order ids look like ORD-1001.
var orders = new Dictionary<string, Order>(StringComparer.OrdinalIgnoreCase)
{
    ["ORD-1001"] = new("ORD-1001", "Delivered", new DateOnly(2026, 11, 2), 49.90m, "Running shoes"),
    ["ORD-1002"] = new("ORD-1002", "Shipped", new DateOnly(2026, 11, 14), 129.00m, "Backpack"),
    ["ORD-1003"] = new("ORD-1003", "Processing", new DateOnly(2026, 11, 17), 19.50m, "Water bottle"),
};

app.MapGet("/readiness", () => Results.Ok());

app.MapPost("/responses", async (JsonNode request) =>
{
    var text = ExtractText(request["input"]);
    var match = Regex.Match(text, @"ORD-\d+", RegexOptions.IgnoreCase);
    var link = Regex.Match(text, @"https://\S+");

    string answer;
    if (link.Success && docClient is not null)
        answer = await ReadReceiptAsync(docClient, await ReceiptOptionsAsync(link.Value));
    else if (!match.Success)
        answer = "No order id found in the request. Order ids look like ORD-1001.";
    else if (orders.TryGetValue(match.Value, out var order))
        answer = JsonSerializer.Serialize(order);
    else
        answer = $"Order {match.Value.ToUpperInvariant()} was not found.";

    return Results.Json(new
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
                content = new[] { new { type = "output_text", text = answer } },
            },
        },
    });
});

app.Run();
return 0;

static bool IsWebLink(string source) =>
    Uri.TryCreate(source, UriKind.Absolute, out var uri) && uri.Scheme == Uri.UriSchemeHttps;

// Where the sample receipt lives (uploaded by create_samplereceipt.bicep). Optional: when set, only this storage account's files are downloaded.
// The address alone opens nothing: the account accepts Entra ID sign-ins only, and this agent runs as the Foundry
// project identity, which has Storage Blob Data Reader on it (create_backendapi.bicep).
static bool IsBlobLink(string source) =>
    Uri.TryCreate(source, UriKind.Absolute, out var uri) && uri.Scheme == Uri.UriSchemeHttps
    && uri.Host.EndsWith(".blob.core.windows.net", StringComparison.OrdinalIgnoreCase)
    && (string.IsNullOrEmpty(Uploads.Account) || uri.Host.Equals($"{Uploads.Account}.blob.core.windows.net", StringComparison.OrdinalIgnoreCase));

// A blob address is downloaded here with this agent's own identity, and its bytes go to Document Intelligence (the
// service can't open a private blob). Any other web link is fetched by the service itself; a local file is sent as bytes.
static async Task<AnalyzeDocumentOptions> ReceiptOptionsAsync(string source)
{
    if (IsBlobLink(source))
    {
        var blob = new BlobClient(new Uri(source), new DefaultAzureCredential());
        var download = await blob.DownloadContentAsync();
        return new AnalyzeDocumentOptions("prebuilt-receipt", download.Value.Content);
    }
    return IsWebLink(source)
        ? new AnalyzeDocumentOptions("prebuilt-receipt", new Uri(source))
        : new AnalyzeDocumentOptions("prebuilt-receipt", BinaryData.FromBytes(await File.ReadAllBytesAsync(source)));
}

static string ExtractText(JsonNode? input)
{
    if (input is JsonValue v && v.TryGetValue<string>(out var s)) return s;
    if (input is JsonArray items)
        return string.Join("\n", items.SelectMany(i => i?["content"] is JsonArray c
            ? c.Select(p => p?["text"]?.GetValue<string>() ?? "")
            : new[] { i?["content"]?.GetValue<string>() ?? "" }));
    return "";
}

// Reads a receipt with the Document Intelligence prebuilt receipt model and returns the key fields as JSON.
// The options carry either a web link (the service fetches it, so it must be reachable: for private storage use
// a short-lived SAS link) or the file's bytes.
static async Task<string> ReadReceiptAsync(DocumentIntelligenceClient client, AnalyzeDocumentOptions options)
{
    Operation<AnalyzeResult> operation = await client.AnalyzeDocumentAsync(WaitUntil.Completed, options);

    var doc = operation.Value.Documents.FirstOrDefault();
    if (doc is null) return "No receipt found in that document.";

    string? Field(string name) => doc.Fields.TryGetValue(name, out var f) ? f.Content : null;
    return JsonSerializer.Serialize(new
    {
        merchant = Field("MerchantName"),
        date = Field("TransactionDate"),
        total = Field("Total"),
        items = doc.Fields.TryGetValue("Items", out var items)
            ? items.ValueList.Select(i => i.ValueDictionary.TryGetValue("Description", out var d) ? d.Content : null)
            : [],
    });
}

static class Uploads
{
    public static readonly string? Account = Environment.GetEnvironmentVariable("STORAGE_ACCOUNT");
}

record Order(string Id, string Status, DateOnly OrderDate, decimal Total, string Item);
