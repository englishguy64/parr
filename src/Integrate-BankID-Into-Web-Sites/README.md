# Integrate BankID Into Web Sites

> BankID is the most trusted way to verify user identity in Sweden. It is issued through all major Swedish Banks.

A simple web site (`index.html` and `app.js`) signs a user in with BankID. The web site cannot call BankID safely on its own, so a small C# backend API does that. It works from a PC (the user scans an animated QR code with the phone) and from a phone (the web site opens the BankID app on the same device).

## Folders

| Folder | Purpose |
|--------|---------|
| `website` | `index.html`, `app.js` and `styles.css`. Only talks to the backend API. It has a **Test or Production** option. `lib/qrcode.js` is the MIT licensed [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) that draws the QR code |
| `backendapi` | ASP.NET minimal API on .NET 10. `Program.cs` has the endpoints, `BankIdClients.cs` reads the certificates from Azure Key Vault, `BankIdClient.cs` calls BankID API v6.0, `BankIdOptions.cs` holds the test and production settings. The backend also serves the `website` folder, so the sign in cookie stays on one address |
| `azure` | Bicep and PowerShell that create the Azure Key Vault and upload the certificates |

## Why the web site needs a backend

1. The BankID service needs a TLS client certificate, and a web site cannot keep it secret
2. The web site must never see the `qrStartSecret` that builds the QR code
3. Only the backend sees the real end user ip, so only it can check it against the ip from `/collect`
4. The backend API, not the web site, decides the user is signed in and starts the session

## The flow

```text
Web site (app.js)             C# backend API                      BankID service
  | POST /api/bankid/start ->  | POST /auth {endUserIp} ---------> |   orderRef, autoStartToken, qrStartToken, qrStartSecret
  |                            |
  | PC:    GET /api/bankid/qr/{orderRef} every second -> bankid.{qrStartToken}.{time}.{HMAC-SHA256(qrStartSecret, time)}
  | Phone: open https://app.bankid.com/?autostarttoken=...   (the backend gives the web site this link)
  |
  | GET /api/bankid/status/{orderRef} every 2 seconds -> | POST /collect --> | pending ... complete (Personal Number, name, ip)
  |                            | checks the ip, starts the session cookie
  | <- Signed in
```

## Test or production, chosen on the web site

The web site has a **BankID Environment** option, Test or Production. The choice is sent with each sign in, and the backend uses that environment's endpoint, certificate and trust store. Both environments are configured side by side, so the same running backend serves both. Anything that is not exactly `production` is treated as test.

| Setting (`BankId:Test` / `BankId:Production`) | Test | Production |
|---------|------|------------|
| `BaseUrl` | `https://appapi2.test.bankid.com/rp/v6.0/` | `https://appapi2.bankid.com/rp/v6.0/` |
| `CertificateSecretName` (Key Vault) | `bankid-test-certificate` (the FPTestcert5 certificate from BankID) | `bankid-production-certificate` (ordered from your bank) |
| `RootCaPath` | `certs/Test-BankID-SSL-Root-CA-v1-Test.pem` | `certs/BankID-SSL-Root-CA-v1.pem` |
| `CheckIp` | `false` (you browse from localhost, BankID sees the phone) | `true` |
| BankID app | Configured for test, with a Test BankID | The real BankID |

Common to both: `BankId:KeyVaultUri` (the vault that holds both certificates) and `BehindProxy` (`true` when a load balancer or App Service sits in front, set in `appsettings.Production.json`).

A call sent to the production environment never shows a login in an app that is configured for test. If nothing appears in the BankID app, check the mode first.

The two public BankID SSL root CA files in `backendapi/certs/` are the certificate authorities that issued the BankID server certificates. They are not secret.

## The certificates are in Azure Key Vault

The backend reads both relying party certificates from Azure Key Vault the first time each mode is used, so test works before you have a production certificate. It signs in to Key Vault with `DefaultAzureCredential`: your `az login` on your PC, or the managed identity when it runs in Azure. Key Vault keeps a certificate and its private key as a secret with the same name, and the backend reads that secret.

1. Create the vault. The script also gives you the Key Vault Certificates Officer role so you can upload, and gives each id in `-BackendPrincipalIds` the Key Vault Secrets User role (read only):
   ```
   cd azure
   $env:TENANT_PREFIX = 'your-tenant-prefix'
   ./01_create-keyvault.ps1
   ```
2. Upload the test certificate. Download the test certificate zip from the [BankID test portal](https://developers.bankid.com/test-portal/test-information). The password is in the README inside the zip:
   ```
   ./02_upload-certificates.ps1 -TestCertificatePath ./FPTestcert5_20240610.p12 -TestCertificatePassword (Read-Host -AsSecureString)
   ```
   Later, when your bank has issued the production certificate, run it again with `-ProductionCertificatePath` and `-ProductionCertificatePassword`
3. Tell the backend where the vault is (the first script prints this line):
   ```
   cd ../backendapi
   dotnet user-secrets set "BankId:KeyVaultUri" "https://<your vault>.vault.azure.net/"
   ```
4. Get a Test BankID. Configure the BankID app for test and create a Test BankID, see the [BankID test portal](https://developers.bankid.com/test-portal/bankid-for-test). Check it works by logging in at https://demo.bankid.com using "Log in with a Test BankID"
5. Start the backend (the `test` launch profile uses the Development environment) and open http://localhost:5300:
   ```
   dotnet run --launch-profile test
   ```
   Choose **Test**. On a PC select **BankID On Another Device** and scan the QR code. On a phone select **BankID On This Device**

When the backend runs in Azure, give its managed identity the Key Vault Secrets User role by passing its object id to `01_create-keyvault.ps1 -BackendPrincipalIds`. The vault has purge protection on, so a deleted certificate cannot be purged for 90 days.

## Requirements for production

1. An agreement with a bank that sells BankID
2. A relying party certificate ordered from that bank. It is not the test certificate
3. The certificate kept secret in Azure Key Vault, read by the backend with its managed identity (never in the web site or in source control)
4. The BankID SSL root CA for production in the backend trust store (`certs/BankID-SSL-Root-CA-v1.pem`)
5. Calls to `https://appapi2.bankid.com/rp/v6.0/` over TLS 1.2 or 1.3 with the certificate
6. The real end user ip sent in every order (`endUserIp`), and a check that it matches the `ip` in the `/collect` result (`CheckIp`)
7. The `qrStartSecret` kept in the backend, and `/collect` called every 2 seconds
8. The certificate renewed before it expires

Also for production: serve the site over HTTPS (the `returnUrl` that brings a phone user back from the BankID app is only sent over HTTPS), replace the in-memory order list in `Program.cs` with a shared cache if you run more than one instance, and follow BankID's guidelines for texts and graphics.

## Docs

- BankID developer site: https://developers.bankid.com
