using System.Collections.Concurrent;
using System.Security.Cryptography.X509Certificates;
using Azure.Identity;
using Azure.Security.KeyVault.Secrets;

// Backend API: the only part that talks to BankID. BankID needs a TLS client certificate, which a web site cannot keep
// secret, and the qrStartSecret must never reach the browser. Test environment only.
var builder = WebApplication.CreateBuilder(args);

var settings = new Settings(
    Url: Env("BANKID_URL", "https://appapi2.test.bankid.com/rp/v6.0/"),
    KeyVaultUri: Env("BANKID_KEYVAULT_URI", ""),
    CertificateName: Env("BANKID_CERTIFICATE_NAME", "fptestcert5"),
    RootCaPath: Path.Combine(AppContext.BaseDirectory, Env("BANKID_ROOT_CA_PATH", "certs/Test-BankID-SSL-Root-CA-v1-Test.pem")),
    WebsiteOrigin: Env("WEBSITE_ORIGIN", "http://localhost:5100").TrimEnd('/'),
    CheckIp: !string.Equals(Env("BANKID_CHECK_IP", "true"), "false", StringComparison.OrdinalIgnoreCase));

builder.Services.AddSingleton(settings);
builder.Services.AddSingleton<SessionStore>();
builder.Services.AddSingleton<Orders>();
// The BankID client is created on first use so the app starts (and /api/health answers) before the certificate is uploaded.
builder.Services.AddSingleton<Lazy<BankIdClient>>(_ => new(() => CreateClient(settings)));
builder.Services.AddCors(o => o.AddDefaultPolicy(p => p
    .WithOrigins(settings.WebsiteOrigin).WithHeaders("Authorization", "Content-Type").WithMethods("GET", "POST")));

var app = builder.Build();
app.UseCors();

app.MapGet("/api/health", () => Results.Ok(new { status = "ok", bankIdEnvironment = "test", keyVaultConfigured = settings.KeyVaultUri != "" }));

// Step 1: start a sign in. The browser says whether it is on the phone itself (same device) or on a PC (QR code).
app.MapPost("/api/bankid/start", async (StartRequest request, HttpContext http, Lazy<BankIdClient> bankId, Orders orders) =>
{
    orders.Purge();
    var returnUrl = request.SameDevice ? settings.WebsiteOrigin + "/" : null;
    var endUserIp = ClientIp(http);
    try
    {
        var auth = await bankId.Value.AuthAsync(endUserIp, returnUrl);
        orders.Add(new Order(auth.OrderRef, auth.QrStartToken, auth.QrStartSecret, endUserIp, DateTimeOffset.UtcNow));
        // Only the autoStartToken goes to the browser, and only to open the BankID app. Never the qrStartSecret.
        var autoStartUrl = $"https://app.bankid.com/?autostarttoken={auth.AutoStartToken}&redirect={Uri.EscapeDataString(returnUrl ?? "null")}";
        return Results.Ok(new { orderRef = auth.OrderRef, autoStartUrl });
    }
    catch (Exception ex) when (ex is BankIdException or InvalidOperationException or Azure.RequestFailedException or Azure.Identity.CredentialUnavailableException)
    {
        app.Logger.LogError(ex, "BankID start failed");
        return Results.Problem("Could not start BankID sign in: " + ex.Message, statusCode: 502);
    }
});

// Step 2 (PC only): the browser asks for a new QR code every second.
app.MapGet("/api/bankid/qr/{orderRef}", (string orderRef, Orders orders) =>
    orders.Find(orderRef) is { } o
        ? Results.Ok(new { qr = BankIdClient.QrData(o.QrStartToken, o.QrStartSecret, o.Created) })
        : Results.NotFound());

// Step 3: the browser polls every 2 seconds. When BankID says complete, the Backend API starts the session.
app.MapGet("/api/bankid/status/{orderRef}", async (string orderRef, Lazy<BankIdClient> bankId, Orders orders, SessionStore sessions) =>
{
    var order = orders.Find(orderRef);
    if (order is null) return Results.NotFound();
    try
    {
        var collect = await bankId.Value.CollectAsync(orderRef);
        if (collect.Status == "pending") return Results.Ok(new { status = "pending", hintCode = collect.HintCode });
        orders.Remove(orderRef);
        if (collect.Status != "complete" || collect.CompletionData is not { } done)
            return Results.Ok(new { status = "failed", hintCode = collect.HintCode });

        if (settings.CheckIp && done.Device.IpAddress != order.EndUserIp)
            return Results.Ok(new { status = "failed", hintCode = "ipMismatch" });

        var user = new SessionStore.SignedInUser(done.User.PersonalNumber, done.User.Name, done.User.GivenName, done.User.Surname);
        return Results.Ok(new { status = "complete", sessionToken = sessions.Create(user), user });
    }
    catch (BankIdException ex)
    {
        app.Logger.LogError(ex, "BankID collect failed");
        orders.Remove(orderRef);
        return Results.Ok(new { status = "failed", hintCode = "internalError" });
    }
});

app.MapPost("/api/bankid/cancel/{orderRef}", async (string orderRef, Lazy<BankIdClient> bankId, Orders orders) =>
{
    if (orders.Find(orderRef) is null) return Results.NoContent();
    orders.Remove(orderRef);
    try { await bankId.Value.CancelAsync(orderRef); } catch (BankIdException) { /* already finished */ }
    return Results.NoContent();
});

// The signed in user, proved by the Bearer session token.
app.MapGet("/api/me", (HttpContext http, SessionStore sessions) =>
    sessions.Find(BearerToken(http)) is { } user ? Results.Ok(user) : Results.Unauthorized());

app.MapPost("/api/signout", (HttpContext http, SessionStore sessions) =>
{
    sessions.Remove(BearerToken(http));
    return Results.NoContent();
});

app.Run();

static string Env(string name, string fallback) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } v ? v : fallback;

static string? BearerToken(HttpContext http) =>
    http.Request.Headers.Authorization.ToString() is { } h && h.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase) ? h[7..].Trim() : null;

// Only the Backend API sees the real end user IP. App Service puts the client in X-Forwarded-For as "ip:port".
static string ClientIp(HttpContext http)
{
    var forwarded = http.Request.Headers["X-Forwarded-For"].ToString().Split(',')[0].Trim();
    if (forwarded.Length > 0)
    {
        if (forwarded.Count(c => c == ':') == 1) forwarded = forwarded[..forwarded.IndexOf(':')]; // strip the port of an IPv4 address
        return forwarded;
    }
    var ip = http.Connection.RemoteIpAddress;
    if (ip is null) return "127.0.0.1";
    return ip.IsIPv4MappedToIPv6 ? ip.MapToIPv4().ToString() : ip.ToString();
}

// The test relying party certificate (FPTestcert5) is a secret in Key Vault. The managed identity reads it, no keys involved.
static BankIdClient CreateClient(Settings s)
{
    if (s.KeyVaultUri == "") throw new InvalidOperationException("BANKID_KEYVAULT_URI is not set, so the BankID certificate cannot be read.");
    var secret = new SecretClient(new Uri(s.KeyVaultUri), new DefaultAzureCredential()).GetSecret(s.CertificateName).Value;
    var certificate = X509CertificateLoader.LoadPkcs12(Convert.FromBase64String(secret.Value), null, X509KeyStorageFlags.EphemeralKeySet);
    var http = new HttpClient(BankIdClient.CreateHandler(s.RootCaPath, certificate)) { BaseAddress = new Uri(s.Url) };
    return new BankIdClient(http);
}

record Settings(string Url, string KeyVaultUri, string CertificateName, string RootCaPath, string WebsiteOrigin, bool CheckIp);

record StartRequest(bool SameDevice);

record Order(string OrderRef, string QrStartToken, string QrStartSecret, string EndUserIp, DateTimeOffset Created);

/// <summary>Orders in progress. BankID orders time out after 3 minutes, so older ones are dropped.</summary>
sealed class Orders
{
    private readonly ConcurrentDictionary<string, Order> orders = new();
    public void Add(Order o) => orders[o.OrderRef] = o;
    public Order? Find(string orderRef) => orders.GetValueOrDefault(orderRef);
    public void Remove(string orderRef) => orders.TryRemove(orderRef, out _);
    public void Purge()
    {
        foreach (var (key, o) in orders)
        {
            if (o.Created < DateTimeOffset.UtcNow.AddMinutes(-5)) orders.TryRemove(key, out _);
        }
    }
}
