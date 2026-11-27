// Backend API: the only part that talks to BankID. The browser calls it directly.
//
//   POST /api/bankid/start            body {device: "pc" | "phone", mode: "test" | "production"}
//                                     -> 200 {orderRef, mode, autoStartToken}   autoStartToken only when device is "phone"
//   GET  /api/bankid/qr/{orderRef}    -> 200 {qrData}   the animated QR code, ask for new data every second
//   GET  /api/bankid/status/{orderRef}-> 200 {status: "pending" | "complete" | "failed", message, sessionToken}   ask about every 2 seconds
//   POST /api/bankid/cancel/{orderRef}-> 204
//   GET  /api/me                      -> 200 the signed in user | 401        Authorization: Bearer <sessionToken>
//   POST /api/signout                 -> 204
//   GET  /health                      -> 200
//                                        502 {message} when BankID or Key Vault could not be reached
//
// The backend holds the relying party certificate (read from Azure Key Vault with its own identity, never kept in the web site)
// and the qrStartSecret. After /collect says complete it starts a session and hands the browser a session token. The token is
// the proof of sign in: the web site and this API are on different addresses, so a cookie would not be sent.
//
// Settings: environment variables (App Service application settings in Azure, set by create_backendapi.bicep).
// None has a default. If one is missing the backend does not start and says which. See BankIdOptions.cs.
using System.Collections.Concurrent;
using System.Security.Cryptography;
using Azure;
using Azure.Identity;
using Microsoft.AspNetCore.HttpOverrides;

var builder = WebApplication.CreateBuilder(args);

var settings = AppSettings.FromEnvironment();
builder.Services.AddSingleton(settings);
builder.Services.AddSingleton<BankIdClients>();

// Only the web site in Azure (BANKID_WEBSITE_URL) may call this API from a browser.
builder.Services.AddCors(options => options.AddDefaultPolicy(policy =>
    policy.WithOrigins(settings.AllowedOrigin).AllowAnyHeader().AllowAnyMethod()));

// Azure App Service sits in front of the app and puts the real end user ip in X-Forwarded-For.
builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
    options.KnownIPNetworks.Clear();
    options.KnownProxies.Clear();
});

var app = builder.Build();
app.UseForwardedHeaders();
app.UseCors();

// Tell the web site what went wrong, for example the certificate is not in Key Vault yet.
app.Use(async (context, next) =>
{
    try
    {
        await next();
    }
    catch (Exception ex) when (ex is BankIdException or RequestFailedException or AuthenticationFailedException
                                   or InvalidOperationException or HttpRequestException or AggregateException)
    {
        app.Logger.LogError(ex, "BankID request failed");
        context.Response.StatusCode = 502;
        await context.Response.WriteAsJsonAsync(new { Message = (ex as AggregateException)?.InnerException?.Message ?? ex.Message });
    }
});

// One entry per order that is waiting for the user, and one per signed in user. In memory, so a restart signs everyone out.
// Use a shared cache such as Redis if you run more than one instance.
var orders = new ConcurrentDictionary<string, Order>();
var sessions = new ConcurrentDictionary<string, Session>();
var sessionLifetime = TimeSpan.FromHours(1);

Session? CurrentSession(HttpRequest request)
{
    var header = request.Headers.Authorization.ToString();
    if (!header.StartsWith("Bearer ", StringComparison.Ordinal)) return null;
    var token = header["Bearer ".Length..];
    if (!sessions.TryGetValue(token, out var session)) return null;
    if (session.Expires > DateTimeOffset.UtcNow) return session;
    sessions.TryRemove(token, out _);
    return null;
}

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

// 1. The web site asks the backend to start a sign in, in test or production mode. Only the backend calls BankID.
app.MapPost("/api/bankid/start", async (StartRequest request, HttpContext context, BankIdClients clients) =>
{
    var endUserIp = context.Connection.RemoteIpAddress?.MapToIPv4().ToString();
    if (endUserIp is null)
    {
        return Results.BadRequest(new { Message = "Could not read the ip address of the user." });
    }

    var mode = BankIdModes.Normalise(request.Mode);
    var client = await clients.GetAsync(mode);

    // The returnUrl brings the user back to the web site after the BankID app on the same phone. BankID wants https, so it
    // is only sent when the web site address is https.
    var auth = await client.AuthAsync(endUserIp, settings.ReturnUrl);
    orders[auth.OrderRef] = new Order(mode, auth.QrStartToken, auth.QrStartSecret, endUserIp, DateTimeOffset.UtcNow);

    // The qrStartSecret never leaves the backend. The autoStartToken is only needed on the same device, so the backend
    // passes it on to the web site only when the user is on the phone.
    var onPhone = request.Device == "phone";
    return Results.Ok(new
    {
        auth.OrderRef,
        Mode = mode,
        AutoStartToken = onPhone ? auth.AutoStartToken : null,
    });
});

// 2. The animated QR code. The web site asks for new QR data every second.
app.MapGet("/api/bankid/qr/{orderRef}", (string orderRef) =>
    orders.TryGetValue(orderRef, out var order)
        ? Results.Ok(new { QrData = BankIdClient.QrData(order.QrStartToken, order.QrStartSecret, order.Created) })
        : Results.NotFound());

// 3. The web site asks for the status about every 2 seconds. The backend calls /collect.
app.MapGet("/api/bankid/status/{orderRef}", async (string orderRef, BankIdClients clients) =>
{
    if (!orders.TryGetValue(orderRef, out var order))
    {
        return Results.NotFound();
    }

    var result = await (await clients.GetAsync(order.Mode)).CollectAsync(orderRef);
    if (result.Status == "pending")
    {
        return Results.Ok(new { Status = "pending", Message = PendingMessage(result.HintCode) });
    }

    orders.TryRemove(orderRef, out _);
    if (result.Status != "complete" || result.CompletionData is null)
    {
        return Results.Ok(new { Status = "failed", Message = FailedMessage(result.HintCode) });
    }

    var data = result.CompletionData;
    if (clients.Settings(order.Mode).CheckIp && data.Device.IpAddress != order.EndUserIp)
    {
        // The user was not on the device that asked for the sign in. Do not sign them in.
        return Results.Ok(new { Status = "failed", Message = "The sign in came from a different network. Try again." });
    }

    // The session token is random, long and only valid for an hour. Nothing in it can be read or forged.
    var sessionToken = Base64Url(RandomNumberGenerator.GetBytes(32));
    sessions[sessionToken] = new Session(data.User.Name, data.User.PersonalNumber, order.Mode, DateTimeOffset.UtcNow + sessionLifetime);
    return Results.Ok(new { Status = "complete", Message = "Signed in", Name = data.User.Name, SessionToken = sessionToken });
});

app.MapPost("/api/bankid/cancel/{orderRef}", async (string orderRef, BankIdClients clients) =>
{
    if (orders.TryRemove(orderRef, out var order))
    {
        await (await clients.GetAsync(order.Mode)).CancelAsync(orderRef);
    }

    return Results.NoContent();
});

// The signed in user. The web site sends the session token it got when the sign in completed.
app.MapGet("/api/me", (HttpRequest request) =>
    CurrentSession(request) is { } session
        ? Results.Ok(new { session.Name, session.PersonalNumber, session.Mode })
        : Results.Unauthorized());

app.MapPost("/api/signout", (HttpRequest request) =>
{
    var header = request.Headers.Authorization.ToString();
    if (header.StartsWith("Bearer ", StringComparison.Ordinal))
    {
        sessions.TryRemove(header["Bearer ".Length..], out _);
    }

    return Results.NoContent();
});

app.Run();

static string Base64Url(byte[] bytes) => Convert.ToBase64String(bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_');

static string PendingMessage(string? hintCode) => hintCode switch
{
    "outstandingTransaction" or "noClient" => "Start the BankID app",
    "started" => "Looking for the BankID. Open the BankID app",
    "userMrtd" => "Check the ID document in the BankID app",
    "userCallConfirm" => "Confirm the call in the BankID app",
    "userSign" => "Enter your security code in the BankID app and select Identify",
    _ => "Waiting for BankID",
};

static string FailedMessage(string? hintCode) => hintCode switch
{
    "expiredTransaction" => "The BankID app did not respond. Try again",
    "userCancel" => "Cancelled in the BankID app",
    "cancelled" => "Cancelled. Try again",
    "startFailed" => "The BankID app did not start. Try again",
    "certificateErr" => "The BankID is blocked or too old. Contact your bank",
    _ => "The sign in failed. Try again",
};

record StartRequest(string Device, string? Mode);

record Order(string Mode, string QrStartToken, string QrStartSecret, string EndUserIp, DateTimeOffset Created);

record Session(string Name, string PersonalNumber, string Mode, DateTimeOffset Expires);
