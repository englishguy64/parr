using System.Buffers.Text;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using BackendApi.Data;

// Back end API for the passkey demo (the front end lives in ../website).
// ASP.NET Core Identity on .NET 10 stores the PUBLIC key of each passkey
// (AspNetUserPasskeys table). The PRIVATE key stays in the user's authenticator:
// a TPM (via Windows Hello), a FIDO2 security key, or another platform authenticator.

var builder = WebApplication.CreateBuilder(args);

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
    ?? throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");
builder.Services.AddDbContext<ApplicationDbContext>(options => options.UseSqlite(connectionString));

// The website (frontend) is a separate origin, so the API must allow it, with cookies.
var frontendOrigin = builder.Configuration["Frontend:Origin"] ?? "http://localhost:5173";
var passkeyDomain = builder.Configuration["Frontend:PasskeyDomain"] ?? "localhost";
builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.WithOrigins(frontendOrigin).AllowAnyHeader().AllowAnyMethod().AllowCredentials()));

builder.Services.AddAuthentication(IdentityConstants.ApplicationScheme).AddIdentityCookies();
builder.Services.AddAuthorization();

builder.Services.AddIdentityCore<ApplicationUser>(options =>
    {
        // Schema version 3 adds the AspNetUserPasskeys table.
        options.Stores.SchemaVersion = IdentitySchemaVersions.Version3;

    })
    .AddEntityFrameworkStores<ApplicationDbContext>()
    .AddSignInManager();

// Passkeys are bound to the website's domain (rp.id), not to this API's host,
// and the browser reports the website as the origin of the WebAuthn ceremony.
builder.Services.Configure<IdentityPasskeyOptions>(options =>
{
    options.ServerDomain = passkeyDomain;
    options.ValidateOrigin = context =>
        ValueTask.FromResult(string.Equals(context.Origin, frontendOrigin, StringComparison.OrdinalIgnoreCase));
});

var app = builder.Build();

// Demo convenience: create the SQLite database (including AspNetUserPasskeys) on start-up.
using (var scope = app.Services.CreateScope())
{
    scope.ServiceProvider.GetRequiredService<ApplicationDbContext>().Database.EnsureCreated();
}

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();

var api = app.MapGroup("/api");

// ---- Who am I, and which passkeys do I have? ----
api.MapGet("/me", async (HttpContext http, UserManager<ApplicationUser> userManager) =>
{
    var user = await userManager.GetUserAsync(http.User);
    if (user is null) return Results.Ok(new { signedIn = false });

    var passkeys = await userManager.GetPasskeysAsync(user);
    return Results.Ok(new
    {
        signedIn = true,
        userName = user.UserName,
        passkeys = passkeys.Select(p => new
        {
            credentialId = Base64Url.EncodeToString(p.CredentialId),
            name = p.Name,
            createdAt = p.CreatedAt,
            signCount = p.SignCount,
            transports = p.Transports,
            isUserVerified = p.IsUserVerified,
            isBackupEligible = p.IsBackupEligible,
            isBackedUp = p.IsBackedUp
        })
    });
});

// ---- 1. Create an account (no password) and sign the new user in so a passkey can be added ----
api.MapPost("/register", async (RegisterRequest request, UserManager<ApplicationUser> userManager,
    SignInManager<ApplicationUser> signInManager) =>
{
    var name = request.UserName?.Trim();
    if (string.IsNullOrEmpty(name)) return Results.BadRequest("Enter a user name.");
    if (await userManager.FindByNameAsync(name) is not null)
        return Results.Conflict("That user name already exists. Sign in with its passkey, then add another.");

    var user = new ApplicationUser { UserName = name };
    var result = await userManager.CreateAsync(user);
    if (!result.Succeeded) return Results.BadRequest(string.Join("; ", result.Errors.Select(e => e.Description)));

    await signInManager.SignInAsync(user, isPersistent: false);
    return Results.Ok(new { userName = user.UserName });
});

// ---- 2. Passkey creation (registration / attestation) ----
// Step A: the server builds the creation options and a random challenge.
api.MapPost("/passkey/creation-options", async (HttpContext http, UserManager<ApplicationUser> userManager,
    SignInManager<ApplicationUser> signInManager) =>
{
    var user = await userManager.GetUserAsync(http.User);
    if (user is null) return Results.Unauthorized();

    var userId = await userManager.GetUserIdAsync(user);
    var userName = await userManager.GetUserNameAsync(user) ?? "User";
    var optionsJson = await signInManager.MakePasskeyCreationOptionsAsync(new()
    {
        Id = userId,
        Name = userName,
        DisplayName = userName
    });
    return Results.Content(optionsJson, "application/json");
});

// Step B: the server verifies the attestation and stores the PUBLIC key with the user.
api.MapPost("/passkey/register", async (PasskeyRequest request, HttpContext http,
    UserManager<ApplicationUser> userManager, SignInManager<ApplicationUser> signInManager) =>
{
    var user = await userManager.GetUserAsync(http.User);
    if (user is null) return Results.Unauthorized();
    if (string.IsNullOrEmpty(request.CredentialJson)) return Results.BadRequest("No credential was supplied.");

    PasskeyAttestationResult attestation;
    try { attestation = await signInManager.PerformPasskeyAttestationAsync(request.CredentialJson); }
    catch (Exception ex) when (ex is System.Text.Json.JsonException or ArgumentException or FormatException or InvalidOperationException)
    {
        return Results.BadRequest("The credential was not valid.");
    }
    if (!attestation.Succeeded)
        return Results.BadRequest($"Could not add the passkey: {attestation.Failure.Message}");

    attestation.Passkey.Name = string.IsNullOrWhiteSpace(request.Name) ? "Passkey" : request.Name.Trim();
    var add = await userManager.AddOrUpdatePasskeyAsync(user, attestation.Passkey);
    return add.Succeeded
        ? Results.Ok(new { credentialId = Base64Url.EncodeToString(attestation.Passkey.CredentialId) })
        : Results.BadRequest("The passkey could not be added to the account.");
}).DisableAntiforgery();

api.MapDelete("/passkey/{credentialId}", async (string credentialId, HttpContext http,
    UserManager<ApplicationUser> userManager) =>
{
    var user = await userManager.GetUserAsync(http.User);
    if (user is null) return Results.Unauthorized();

    byte[] id;
    try { id = Base64Url.DecodeFromChars(credentialId); }
    catch (FormatException) { return Results.BadRequest("Invalid credential id."); }

    var result = await userManager.RemovePasskeyAsync(user, id);
    return result.Succeeded ? Results.NoContent() : Results.BadRequest("The passkey could not be deleted.");
});

// ---- 3. Sign in (authentication / assertion) ----
// Step A: a fresh random challenge. Without a user name this is a "discoverable" passkey sign in.
api.MapPost("/passkey/request-options", async (string? username, UserManager<ApplicationUser> userManager,
    SignInManager<ApplicationUser> signInManager) =>
{
    var user = string.IsNullOrWhiteSpace(username) ? null : await userManager.FindByNameAsync(username.Trim());
    var optionsJson = await signInManager.MakePasskeyRequestOptionsAsync(user);
    return Results.Content(optionsJson, "application/json");
});

// Step B: verify the signature with the stored public key and issue the auth cookie.
api.MapPost("/passkey/login", async (PasskeyRequest request, SignInManager<ApplicationUser> signInManager) =>
{
    if (string.IsNullOrEmpty(request.CredentialJson)) return Results.BadRequest("No credential was supplied.");

    try
    {
        var result = await signInManager.PasskeySignInAsync(request.CredentialJson);
        return result.Succeeded ? Results.Ok() : Results.BadRequest("Passkey sign in failed.");
    }
    catch (Exception ex) when (ex is System.Text.Json.JsonException or ArgumentException or FormatException or InvalidOperationException)
    {
        return Results.BadRequest("The credential was not valid.");
    }
});

api.MapPost("/logout", async (SignInManager<ApplicationUser> signInManager) =>
{
    await signInManager.SignOutAsync();
    return Results.NoContent();
});

app.Run();

record RegisterRequest(string? UserName);
record PasskeyRequest(string? CredentialJson, string? Name);
