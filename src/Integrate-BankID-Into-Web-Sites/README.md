# Integrate BankID Into Web Sites

> BankID is the most trusted way to verify user identity in Sweden. It is issued through all major Swedish banks.

**Work in progress. BankID test environment only. Use with caution.**

**Read the [BankID test portal guide](https://developers.bankid.com/test-portal/testing) before starting.** You can also read the [BankID developers page](https://developers.bankid.com).

A web site signs a user in with BankID. The web site cannot call BankID safely on its own, so a Backend API does that. It works from a PC (the user scans an animated QR code with the phone) and from a phone (the web site opens the BankID app on the same device). This sample uses the **BankID test environment only**. It is an **Azure** solution: two App Services and a Key Vault. If the web site is opened on localhost the sign in is fake, and the page says so.

## Architecture

```text
Browser --(GET page, config.json)------------> Web site (App Service)      static files, config.json says where the Backend API is
   |
   '--(sign in calls, Bearer session token)--> Backend API (App Service)   the only part that talks to BankID
                                                  |  managed identity, no keys
                                                  |--> Azure Key Vault          test relying party certificate (FPTestcert5)
                                                  '--> BankID test service      TLS client certificate
                                                       https://appapi2.test.bankid.com/rp/v6.0/
```

| Folder | Purpose |
|--------|---------|
| `website` | Plain HTML and JavaScript, nothing to build. `config.json` says where the Backend API is (the deploy script writes the Azure address into it). `lib/qrcode.js` is the MIT licensed [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) that draws the QR code |
| `backendapi` | ASP.NET minimal API on .NET 10. `Program.cs` has the endpoints, `BankIdClient.cs` calls BankID API v6.0, `SessionStore.cs` holds signed in users. `certs/` holds the public BankID **test** root CA |
| `azure` | Numbered PowerShell scripts and Bicep that create the Key Vault, the App Service plan and both web apps, and deploy the code |

## Why the web site needs a Backend API

1. BankID needs a TLS client certificate, and a web site cannot keep it secret
2. The web site must never see the `qrStartSecret` that builds the QR code, so the Backend API sends only the finished QR text
3. Only the Backend API sees the real end user IP, so only it can compare it with the IP BankID reports from `/collect`
4. The Backend API, not the web site, decides the user is signed in

## The flow

```text
Browser                       Backend API                          BankID service
  | POST /api/bankid/start ->   | POST /auth {endUserIp, returnUrl} -> | orderRef, autoStartToken, qrStartToken, qrStartSecret
  | PC:    GET /api/bankid/qr/{orderRef} every second -> bankid.{qrStartToken}.{time}.{HMAC-SHA256(qrStartSecret, time)}
  | Phone: open https://app.bankid.com/?autostarttoken=...&redirect=...
  | GET /api/bankid/status/{orderRef} every 2 seconds -> | POST /collect -> pending ... complete
  |                             | checks the IP, starts a session
  | <- sessionToken             |
  | GET /api/me  (Authorization: Bearer <sessionToken>)
```

The web site and the Backend API are on different addresses, so a cookie would not travel between them. The proof of sign in is a random 256 bit session token, valid for an hour, held in the Backend API memory and in the browser tab session storage. The Backend API accepts calls only from the web site address (CORS). A restart signs everyone out. Use a shared cache such as Redis if you run more than one instance.

On the same device the browser leaves for the BankID app and comes back, so the page keeps the order reference in session storage and carries on polling when it returns.

## Settings (Backend API app settings, set by `create_backendapi.bicep`)

| Setting | Value |
|---------|-------|
| `BANKID_URL` | `https://appapi2.test.bankid.com/rp/v6.0/` |
| `BANKID_KEYVAULT_URI` | Key Vault address |
| `BANKID_CERTIFICATE_NAME` | `fptestcert5` |
| `BANKID_ROOT_CA_PATH` | `certs/Test-BankID-SSL-Root-CA-v1-Test.pem` (default) |
| `BANKID_CHECK_IP` | `true`. Set `false` if the phone and the browser are on different networks (for example phone on mobile data, PC on wifi) |
| `WEBSITE_ORIGIN` | The web site address allowed by CORS |

## Run locally

```powershell
npx serve website -l 5100
```

The page works but the sign in is **fake** because BankID is not called. To test against BankID you must deploy to Azure (the Backend API reads the certificate from Key Vault with its managed identity).

## Deploy to Azure

Prerequisites: Azure CLI (logged in), .NET 10 SDK, PowerShell.

1. Get the public BankID **test** certificate (FPTestcert, a `.p12` file) and its password from [developers.bankid.com](https://developers.bankid.com) (search for "test certificate"). Pass them to script 02 with `-CertificatePath` and `-CertificatePassword`. Never commit the file (`*.p12` is in `.gitignore`).
2. Set a unique prefix and run the scripts in `azure/` in order:

```powershell
$env:RECEIPE_PREFIX = 'myuniqueprefix'
./azure/01_create-keyvault.ps1                                   # add -PreviewOnly to see the what-if first
./azure/02_upload-test-certificate.ps1 -CertificatePath C:\path\FPTestcert5.p12
./azure/03_create-backendapi.ps1
./azure/04_deploy-backendapi.ps1
./azure/05_create-webapp.ps1
./azure/06_deploy-webapp.ps1
```

3. Check `https://<prefix>-bankid-api.azurewebsites.net/api/health`, then open `https://<prefix>-bankid-web.azurewebsites.net`.
4. Remove everything with `./azure/99_delete-resourcegroup.ps1`. The Key Vault has purge protection, so its name stays reserved for 7 days.

## Sign in with a test user

1. Install the BankID app on a phone, then switch it to the test environment (see the BankID test guide: tap the app version 5 times, or use the test-mode link described at developers.bankid.com).
2. Create a test BankID for a test personal number by following the guide on the [BankID developers page](https://developers.bankid.com).
3. On the web site choose **another device** and scan the QR code, or **this device** on the phone.
