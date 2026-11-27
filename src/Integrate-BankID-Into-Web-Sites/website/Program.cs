// Web site for BankID sign in. It only serves the page and tells the page where to go:
//
//   Browser --(GET /config.json)--> this web site       where is the Backend API?
//   Browser --(sign in calls)-----> Backend API --(TLS client certificate from Key Vault)--> BankID
//
// The browser calls the Backend API directly. The Backend API is the only part that talks to BankID, because only it holds
// the relying party certificate. This web site never sees a certificate, a BankID secret or the user's session.
//
// The solution works in Azure only. If the page is opened on localhost (for example with dotnet run on a PC) there is no Backend
// API to call, so the sign in is fake: this app answers the sign in calls itself and the page says so. Nothing is sent to BankID.
//
// Setting (App Service application setting in Azure, set by 05_create-webapp.ps1). It is not a secret and it has no default:
//   BACKEND_API_URL   the address of the Backend API, for example https://<prefix>-api.azurewebsites.net
using System.Collections.Concurrent;
using System.Net;
using System.Security.Cryptography;

var builder = WebApplication.CreateBuilder(args);

var backendApiUrl = Environment.GetEnvironmentVariable("BACKEND_API_URL")?.Trim().TrimEnd('/');
if (!string.IsNullOrEmpty(backendApiUrl)
    && (!Uri.TryCreate(backendApiUrl, UriKind.Absolute, out var backendUri)
        || (backendUri.Scheme != Uri.UriSchemeHttps && backendUri.Scheme != Uri.UriSchemeHttp)))
{
    throw new InvalidOperationException("BACKEND_API_URL must be the address of the Backend API, for example https://<prefix>-api.azurewebsites.net");
}

var app = builder.Build();
app.UseDefaultFiles();
app.UseStaticFiles();

// Running on localhost: the address in the browser is localhost, 127.0.0.1 or ::1.
static bool OnLocalhost(HttpContext context)
{
    var host = context.Request.Host.Host;
    return host.Equals("localhost", StringComparison.OrdinalIgnoreCase)
           || (IPAddress.TryParse(host.Trim('[', ']'), out var address) && IPAddress.IsLoopback(address));
}

// What the page needs. On localhost: use the fake sign in. In Azure: where the Backend API is. No secrets: a browser can't keep one.
app.MapGet("/config.json", (HttpContext context) =>
{
    if (OnLocalhost(context)) return Results.Json(new { fake = true });
    if (string.IsNullOrEmpty(backendApiUrl))
        return Results.Json(new { message = "BACKEND_API_URL is not set on this web site." }, statusCode: StatusCodes.Status500InternalServerError);
    return Results.Json(new { fake = false, backendApiUrl });
});

// ---------- fake sign in, only on localhost ----------
// The page's whole sign in flow (the Test or Production option, the QR code, waiting and polling, signed in) can be tried on a PC
// without Azure, a certificate or a BankID. The user it signs in is made up. In Azure these calls answer "not found".
var fakeOrders = new ConcurrentDictionary<string, DateTime>();
var fakeSessions = new ConcurrentDictionary<string, string>();   // session token -> mode

string NewToken() => "fake-" + Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(16));
string Bearer(HttpRequest request) => request.Headers.Authorization.ToString().Replace("Bearer ", "");

app.MapPost("/api/bankid/start", (HttpContext context, FakeStart request) =>
{
    if (!OnLocalhost(context)) return Results.NotFound();
    var orderRef = NewToken();
    fakeOrders[orderRef] = DateTime.UtcNow;
    return Results.Ok(new
    {
        orderRef,
        mode = request.Mode == "production" ? "production" : "test",
        autoStartToken = (string?)null,   // the fake sign in never starts the BankID app
    });
});

app.MapGet("/api/bankid/qr/{orderRef}", (HttpContext context, string orderRef) =>
    OnLocalhost(context) && fakeOrders.TryGetValue(orderRef, out var started)
        ? Results.Ok(new { qrData = $"bankid.fake.{(int)(DateTime.UtcNow - started).TotalSeconds}.not-a-real-code" })
        : Results.NotFound());

app.MapGet("/api/bankid/status/{orderRef}", (HttpContext context, string orderRef) =>
{
    if (!OnLocalhost(context) || !fakeOrders.TryGetValue(orderRef, out var started)) return Results.NotFound();
    var seconds = (DateTime.UtcNow - started).TotalSeconds;
    if (seconds < 3) return Results.Ok(new { status = "pending", message = "Start the BankID app (fake sign in: nothing is sent)" });
    if (seconds < 6) return Results.Ok(new { status = "pending", message = "Enter your security code in the BankID app (fake sign in)" });

    fakeOrders.TryRemove(orderRef, out _);
    var token = NewToken();
    fakeSessions[token] = "test";
    return Results.Ok(new { status = "complete", message = "Signed in", name = "Fake User", sessionToken = token });
});

app.MapPost("/api/bankid/cancel/{orderRef}", (HttpContext context, string orderRef) =>
{
    if (!OnLocalhost(context)) return Results.NotFound();
    fakeOrders.TryRemove(orderRef, out _);
    return Results.NoContent();
});

app.MapGet("/api/me", (HttpContext context) =>
    OnLocalhost(context) && fakeSessions.ContainsKey(Bearer(context.Request))
        ? Results.Ok(new { name = "Fake User", personalNumber = "199001019999", mode = "test" })
        : Results.Unauthorized());

app.MapPost("/api/signout", (HttpContext context) =>
{
    if (!OnLocalhost(context)) return Results.NotFound();
    fakeSessions.TryRemove(Bearer(context.Request), out _);
    return Results.NoContent();
});

app.Run();

record FakeStart(string Device, string? Mode);
