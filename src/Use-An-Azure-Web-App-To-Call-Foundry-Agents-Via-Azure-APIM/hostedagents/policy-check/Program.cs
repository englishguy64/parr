// Policy Check Hosted Agent: applies the return and refund rules to an order.
//
// Like Order Lookup, this earns a container because it runs your own code, not just a prompt: the rules below are
// plain C#, so the answer is the same every time. Replace them with your real policy (or a call to a policy service).
//
// Runs as a container in Foundry Agent Service. Foundry calls POST /responses on port 8088.
// The orchestrator sends it the order details it got from Order Lookup, for example the JSON
//   {"Id":"ORD-1001","Status":"Delivered","OrderDate":"2026-11-02","Total":49.90,"Item":"Running shoes"}
// and this agent replies with a decision:  approved | manual_review | denied | needs_more_info.
//
// Rules (all stand-ins):
//   1. The order must be Delivered, otherwise it can't be returned yet.
//   2. Returns are accepted within 30 days of the order date.
//   3. Gift cards, perishable and personalised items can't be returned.
//   4. Refunds over 100 need a person to review them.
//
// Try it on your PC (no Azure needed):
//   dotnet run -- "{\"Id\":\"ORD-1001\",\"Status\":\"Delivered\",\"OrderDate\":\"2026-11-02\",\"Total\":49.90,\"Item\":\"Running shoes\"}"
// With no argument, `dotnet run` starts the agent as usual.
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

const int ReturnWindowDays = 30;
const decimal ManualReviewOver = 100m;
string[] nonReturnable = ["gift card", "perishable", "personalised", "personalized", "custom"];

// Local test mode: `dotnet run -- "<order text>"` prints the decision and exits.
if (args.Length == 1 && !args[0].StartsWith("--"))
{
    Console.WriteLine(Evaluate(args[0], DateOnly.FromDateTime(DateTime.UtcNow)));
    return 0;
}

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/readiness", () => Results.Ok());

app.MapPost("/responses", (JsonNode request) =>
{
    var answer = Evaluate(ExtractText(request["input"]), DateOnly.FromDateTime(DateTime.UtcNow));

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

// Applies the rules to the request text and returns the decision as JSON.
string Evaluate(string text, DateOnly today)
{
    string Decide(string decision, string reason, string? orderId = null) =>
        JsonSerializer.Serialize(new { decision, reason, orderId });

    var orderId = Regex.Match(text, @"ORD-\d+", RegexOptions.IgnoreCase) is { Success: true } m
        ? m.Value.ToUpperInvariant() : null;

    // Rule 1: only delivered orders can be returned.
    if (Regex.IsMatch(text, @"\b(Shipped|Processing|Cancelled)\b", RegexOptions.IgnoreCase) &&
        !Regex.IsMatch(text, @"\bDelivered\b", RegexOptions.IgnoreCase))
        return Decide("denied", "The order has not been delivered, so it can't be returned yet.", orderId);

    // Rule 3: items that can't be returned.
    var blocked = nonReturnable.FirstOrDefault(w => text.Contains(w, StringComparison.OrdinalIgnoreCase));
    if (blocked is not null)
        return Decide("denied", $"Items of type '{blocked}' can't be returned.", orderId);

    // Rule 2: the return window, counted from the first date in the request (the order date).
    var dateMatch = Regex.Match(text, @"\d{4}-\d{2}-\d{2}");
    if (!dateMatch.Success || !DateOnly.TryParse(dateMatch.Value, out var orderDate))
        return Decide("needs_more_info", "No order date found. Send the order details, including the date (yyyy-mm-dd).", orderId);

    var age = today.DayNumber - orderDate.DayNumber;
    if (age > ReturnWindowDays)
        return Decide("denied", $"The order is {age} days old; returns are accepted within {ReturnWindowDays} days.", orderId);

    // Rule 4: large refunds need a person to look at them.
    var totalMatch = Regex.Match(text, @"""?total""?\s*[:=]\s*(\d+(?:\.\d+)?)", RegexOptions.IgnoreCase);
    if (!totalMatch.Success)
        return Decide("needs_more_info", "No order total found. Send the order details, including the total.", orderId);

    var total = decimal.Parse(totalMatch.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture);
    return total > ManualReviewOver
        ? Decide("manual_review", $"The refund of {total} is over {ManualReviewOver}, so a person must approve it.", orderId)
        : Decide("approved", $"Within {ReturnWindowDays} days and under {ManualReviewOver}: the return can be accepted.", orderId);
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
