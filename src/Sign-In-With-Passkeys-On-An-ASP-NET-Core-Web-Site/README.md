# Passkey demo: WebAuthn front end + ASP.NET Core Identity API

Passwordless sign-in with passkeys, split into two separate projects:

| Folder | What it is | URL |
|---|---|---|
| `backendapi/` | ASP.NET Core Identity API (.NET 10, SQLite) | http://localhost:5080 |
| `website/` | Static front end (HTML + JavaScript, WebAuthn) | http://localhost:5173 |

## Run it

```
cd backendapi
dotnet run

cd website
npx serve -l 5173 .        # or: python -m http.server 5173
```

Open http://localhost:5173. Use `localhost`, not `127.0.0.1`: a passkey is bound to its domain.

## What is a passkey?

A passkey is a public/private key pair.

- The **private key** is created by, and never leaves, the user's authenticator:
  - **Windows Hello**, with the key held in the PC's TPM 2.0 chip (`platform` attachment), or
  - a **FIDO2 security key** over USB, NFC or BLE (`cross-platform` attachment).
- The **public key** is sent to the server and stored in the `AspNetUserPasskeys` table.
- The server holds nothing secret. There is no password to steal or phish.

## How the pieces fit

```
Browser (website)                          backendapi (Identity)
-----------------                          ---------------------
app.js  --- fetch + cookie (CORS) ------>  /api/* minimal API endpoints
   |                                          |
navigator.credentials.create/get              SignInManager (passkey methods)
   |                                          |
Authenticator (TPM / FIDO2 key)               SQLite: AspNetUsers, AspNetUserPasskeys
```

### Registration (create a passkey)

1. `POST /api/register` creates the user (no password) and signs them in with a cookie.
2. `POST /api/passkey/creation-options`: the server returns options with a random challenge,
   the relying party id and the user id (`MakePasskeyCreationOptionsAsync`).
3. `app.js` picks the authenticator (`authenticatorAttachment`), requires a discoverable key
   (`residentKey: required`) and user verification (PIN, fingerprint or face), then calls
   `navigator.credentials.create()`.
4. `POST /api/passkey/register`: the browser sends the attestation and the server verifies it
   (`PerformPasskeyAttestationAsync`) and stores the **public key** (`AddOrUpdatePasskeyAsync`).

### Sign in (authenticate)

1. `POST /api/passkey/request-options`: the server returns a **new random challenge**
   (`MakePasskeyRequestOptionsAsync`). With no user name this is a discoverable sign-in,
   where the browser offers any passkey it has for the site.
2. `app.js` calls `navigator.credentials.get()`. The authenticator signs the challenge with the private key.
3. `POST /api/passkey/login`: the server checks the signature against the stored public key and
   the sign count (`PasskeySignInAsync`), then issues the Identity auth cookie.

### Other endpoints

- `GET /api/me`: the current user and their passkeys.
- `DELETE /api/passkey/{credentialId}`: remove a passkey.
- `POST /api/logout`: sign out.

## Why a separate front end needs extra setup

The website and the API are different origins (different ports), so:

- **CORS** (`Program.cs`): the API allows only the website origin, with credentials, so the
  auth cookie is accepted. `app.js` sends `credentials: 'include'` on every request.
- **Passkey domain**: a passkey is bound to the relying party id, here `localhost`
  (`IdentityPasskeyOptions.ServerDomain`). By default Identity would use the API's host.
- **Origin check**: the browser reports the website as the origin of the WebAuthn ceremony.
  `IdentityPasskeyOptions.ValidateOrigin` accepts only that origin.
- **Cookies**: `localhost` on two ports counts as the same site, so the default cookie settings work.
  A production deployment on separate domains would need a shared parent domain
  (for example `app.example.com` and `api.example.com`) and `SameSite`/`Secure` cookie settings.

## Configuration

- `backendapi/appsettings.json`:
  - `Frontend:Origin`: the website origin allowed by CORS and WebAuthn (`http://localhost:5173`).
  - `Frontend:PasskeyDomain`: the relying party id (`localhost`).
  - `ConnectionStrings:DefaultConnection`: the SQLite file (`passkeys.db`).
- `website/app.js`: `API_BASE`, the API address (`http://localhost:5080`).

## Project layout

```
backendapi/
  Program.cs                  Identity, CORS, passkey options and all endpoints
  Data/ApplicationUser.cs     IdentityUser (no password is ever set)
  Data/ApplicationDbContext.cs  IdentityDbContext, schema version 3 (adds AspNetUserPasskeys)
website/
  index.html                  Page and styling
  app.js                      WebAuthn calls and UI logic
```

## Notes

- The database is created with `EnsureCreated()` on start-up. This is for the demo only,
  so use EF Core migrations in a real application.
- Passkeys need a secure context. `http://localhost` is treated as secure, anything else needs HTTPS.
- Add more than one passkey per account so a lost authenticator does not lock the user out.
- The browser must support `PublicKeyCredential.parseCreationOptionsFromJSON` and
  `parseRequestOptionsFromJSON` (current Edge, Chrome, Safari or Firefox).
