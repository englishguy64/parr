using System.Collections.Concurrent;
using Azure;
using Azure.Identity;
using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.Extensions.FileProviders;

var builder = WebApplication.CreateBuilder(args);

// Both environments are configured side by side. The web site chooses test or production for each sign in.
builder.Services.Configure<BankIdOptions>(builder.Configuration.GetSection("BankId"));
builder.Services.AddSingleton<BankIdClients>();
var behindProxy = builder.Configuration.GetValue<bool>("BehindProxy");

builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.Cookie.HttpOnly = true;
        options.Cookie.SameSite = SameSiteMode.Lax;
        options.Cookie.SecurePolicy = CookieSecurePolicy.SameAsRequest;
        options.ExpireTimeSpan = TimeSpan.FromHours(1);
        options.Events.OnRedirectToLogin = context => { context.Response.StatusCode = 401; return Task.CompletedTask; };
    });
builder.Services.AddAuthorization();

if (behindProxy)
{
    // Behind a load balancer or App Service the real end user ip is in X-Forwarded-For.
    builder.Services.Configure<ForwardedHeadersOptions>(options =>
    {
        options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
        options.KnownIPNetworks.Clear();
        options.KnownProxies.Clear();
    });
}

var app = builder.Build();

if (behindProxy)
{
    app.UseForwardedHeaders();
}

// Tell the web site what went wrong, for example the certificate is not in Key Vault yet.
app.Use(async (context, next) =>
{
    try
    {
        await next();
    }
    catch (Exception ex) when (ex is BankIdException or RequestFailedException or AuthenticationFailedException
                                   or InvalidOperationException or HttpRequestException)
    {
        app.Logger.LogError(ex, "BankID request failed");
        context.Response.StatusCode = 502;
        await context.Response.WriteAsJsonAsync(new { Message = ex.Message });
    }
});

// The simple web site (index.html, app.js) is served from the same address, so the sign in cookie stays on one origin.
var webSitePath = Path.GetFullPath(app.Configuration["WebSite:Path"] ?? "../website", app.Environment.ContentRootPath);
var webSiteFiles = new PhysicalFileProvider(webSitePath);
app.UseDefaultFiles(new DefaultFilesOptions { FileProvider = webSiteFiles });
app.UseStaticFiles(new StaticFileOptions { FileProvider = webSiteFiles });

app.UseAuthentication();
app.UseAuthorization();

// One entry per order that is waiting for the user. Use a shared cache such as Redis if you run more than one instance.
var orders = new ConcurrentDictionary<string, Order>();

// 1. The web site asks the backend to start a sign in, in test or production mode. Only the backend calls BankID.
app.MapPost("/api/bankid/start", async (StartRequest request, HttpContext context, BankIdClients clients) =>
{
    var mode = BankIdModes.Normalise(request.Mode);
    var client = await clients.GetAsync(mode);
    var endUserIp = context.Connection.RemoteIpAddress?.MapToIPv4().ToString() ?? "127.0.0.1";

    // returnUrl brings the user back to the web site after the BankID app on the same phone. BankID wants https.
    var returnUrl = context.Request.IsHttps ? $"https://{context.Request.Host}/" : null;

    var auth = await client.AuthAsync(endUserIp, returnUrl);
    orders[auth.OrderRef] = new Order(mode, auth.QrStartToken, auth.QrStartSecret, endUserIp, DateTimeOffset.UtcNow);

    // The qrStartSecret never leaves the backend. The autoStartToken is only needed on the same device.
    var launchUrl = request.Device == "phone"
        ? $"https://app.bankid.com/?autostarttoken={auth.AutoStartToken}" + (returnUrl is null ? "&redirect=null" : "")
        : null;
    return Results.Ok(new { auth.OrderRef, Mode = mode, LaunchUrl = launchUrl });
});

// 2. The animated QR code. The web site asks for new QR data every second.
app.MapGet("/api/bankid/qr/{orderRef}", (string orderRef) =>
    orders.TryGetValue(orderRef, out var order)
        ? Results.Ok(new { QrData = BankIdClient.QrData(order.QrStartToken, order.QrStartSecret, order.Created) })
        : Results.NotFound());

// 3. The web site asks for the status about every 2 seconds. The backend calls /collect.
app.MapGet("/api/bankid/status/{orderRef}", async (string orderRef, HttpContext context, BankIdClients clients) =>
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

    var claims = new List<Claim>
    {
        new(ClaimTypes.Name, data.User.Name),
        new("personalNumber", data.User.PersonalNumber),
        new("mode", order.Mode),
    };
    var identity = new ClaimsIdentity(claims, CookieAuthenticationDefaults.AuthenticationScheme);
    await context.SignInAsync(new ClaimsPrincipal(identity));
    return Results.Ok(new { Status = "complete", Message = "Signed in", Name = data.User.Name });
});

app.MapPost("/api/bankid/cancel/{orderRef}", async (string orderRef, BankIdClients clients) =>
{
    if (orders.TryRemove(orderRef, out var order))
    {
        await (await clients.GetAsync(order.Mode)).CancelAsync(orderRef);
    }

    return Results.NoContent();
});

// The session the backend started. The web site only ever sees this cookie, never a BankID secret.
app.MapGet("/api/me", (ClaimsPrincipal user) =>
    user.Identity?.IsAuthenticated == true
        ? Results.Ok(new
        {
            Name = user.Identity.Name,
            PersonalNumber = user.FindFirstValue("personalNumber"),
            Mode = user.FindFirstValue("mode"),
        })
        : Results.Unauthorized());

app.MapPost("/api/signout", async (HttpContext context) =>
{
    await context.SignOutAsync();
    return Results.NoContent();
});

app.Run();

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
