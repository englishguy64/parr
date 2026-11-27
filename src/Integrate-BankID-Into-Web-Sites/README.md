# Integrate BankID Into Web Sites

> BankID is the most trusted way to verify user identity in Sweden. It is issued through all major Swedish Banks.

A web site signs a user in with BankID. The web site cannot call BankID safely on its own, so a Backend API does that. It works from a PC (the user scans an animated QR code with the phone) and from a phone (the web site opens the BankID app on the same device). The web site has a **Test or Production** option.

The structure follows the Use An Azure Web App to Call Foundry Agents recipe: a small web site that only serves the page and tells it where to go, a separate Backend API, and numbered Bicep and PowerShell scripts. It is an **Azure only** solution. If the web site is opened on localhost the sign in is fake, and the page says so.

## Architecture

```text
Browser ──(GET /config.json)──────────────────► Web site (App Service)      serves the page, says where the Backend API is
   │
   └─(sign in calls, Bearer session token)────► Backend API (App Service)    the only part that talks to BankID
                                                   │  managed identity, no keys
                                                   ├──► Azure Key Vault (test)        relying party certificate for test
                                                   ├──► Azure Key Vault (production)  relying party certificate for production
                                                   └──► BankID service (TLS client certificate)
```

| Folder | Purpose |
|--------|---------|
| `website` | A small ASP.NET app. `Program.cs` serves the page in `wwwroot` and `/config.json`. `wwwroot` is `index.html`, `app.js`, `styles.css` and `lib/qrcode.js`, the MIT licensed [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) that draws the QR code. On localhost it answers the sign in calls itself with a fake sign in
| `backendapi` | ASP.NET minimal API on .NET 10. `Program.cs` has the endpoints, `BankIdClients.cs` reads the certificates from Azure Key Vault, `BankIdClient.cs` calls BankID API v6.0, `BankIdOptions.cs` reads the settings. `certs/` holds the public BankID root CA files |
| `azure` | Numbered Bicep and PowerShell scripts that create the Key Vaults and create and deploy the Backend API and the web site. The certificates are uploaded by hand |

## Why the web site needs a Backend API

1. The BankID service needs a TLS client certificate, and a web site cannot keep it secret
2. The web site must never see the `qrStartSecret` that builds the QR code
3. Only the Backend API sees the real end user ip, so only it can check it against the ip from `/collect`
4. The Backend API, not the web site, decides the user is signed in and starts the session

## The flow

```text
Web site                      Backend API                         BankID service
  | POST /api/bankid/start ->  | POST /auth {endUserIp, returnUrl} -> |   orderRef, autoStartToken, qrStartToken, qrStartSecret
  |                            |
  | PC:    GET /api/bankid/qr/{orderRef} every second -> bankid.{qrStartToken}.{time}.{HMAC-SHA256(qrStartSecret, time)}
  | Phone: the Backend API gives the web site the autoStartToken, and the web site opens https://app.bankid.com/?autostarttoken=...
  |
  | GET /api/bankid/status/{orderRef} every 2 seconds -> | POST /collect --> | pending ... complete (Personal Number, name, ip)
  |                            | checks the ip, starts a session
  | <- sessionToken            |
  | GET /api/me  (Authorization: Bearer <sessionToken>)  -> the signed in user
```

The web site and the Backend API are on different addresses, so a cookie would not be sent between them. The proof of sign in is a session token: random, 256 bits, valid for an hour, held in the Backend API's memory and in the browser tab's session storage. The Backend API only accepts calls from the web site's address (CORS). A restart of the Backend API signs everyone out. Use a shared cache such as Redis if you run more than one instance.

## Test or production, chosen on the web site

The web site has a **BankID Environment** option, Test or Production. The choice is sent with each sign in, and the Backend API uses that environment's endpoint, certificate and trust store. Both environments are configured side by side. Anything that is not exactly `production` is treated as test.

| Environment variable (`BANKID_TEST_...` / `BANKID_PRODUCTION_...`) | Test | Production |
|---------|------|------------|
| `..._URL` | `https://appapi2.test.bankid.com/rp/v6.0/` | `https://appapi2.bankid.com/rp/v6.0/` |
| `..._KEYVAULT_URI` | The test Key Vault | The production Key Vault, a separate vault |
| `..._CERTIFICATE_NAME` (Key Vault) | `fptestcert5`, the public BankID test certificate FPTestcert5. **Uploaded by hand** | for example `bankid-production-certificate` (ordered from your bank). **Uploaded by hand** |
| `..._ROOT_CA_PATH` | `certs/Test-BankID-SSL-Root-CA-v1-Test.pem` | `certs/BankID-SSL-Root-CA-v1.pem` |
| `..._CHECK_IP` | `false` (the phone may be on another network than the browser) | `true` |
| BankID app | Configured for test, with a Test BankID | The real BankID |

A call sent to the production environment never shows a login in an app that is configured for test. If nothing appears in the BankID app, check the mode first.

The two public BankID SSL root CA files in `backendapi/certs/` are the certificate authorities that issued the BankID server certificates. They are not secret. They are not your certificate: your relying party certificate, which proves your organisation to BankID, is the secret one and lives in Key Vault.

## Settings are environment variables, with no defaults

Nothing has a default value. The apps and the scripts read environment variables, and stop with a message that lists every variable that is missing. In Azure the variables are the apps' application settings, which the Bicep sets. Locally you set them in your PowerShell session.

**Web site** (`website/Program.cs`):

| Variable | Meaning |
|----------|---------|
| `BACKEND_API_URL` | The address of the Backend API. The page calls it directly. Script 04 sets it in Azure. It has no default: without it the web site answers "BACKEND_API_URL is not set" (on localhost it is not used, the sign in is fake) |

**Backend API** (`backendapi/BankIdOptions.cs`):

| Variable | Meaning |
|----------|---------|
| `BANKID_WEBSITE_URL` | The address of the web site in Azure. It is the only address allowed to call the Backend API from a browser, and BankID returns a phone user to it after the BankID app. Script 03 builds it as `https://<prefix>-web.azurewebsites.net/` |
| `BANKID_TEST_URL`, `BANKID_TEST_KEYVAULT_URI`, `BANKID_TEST_CERTIFICATE_NAME`, `BANKID_TEST_ROOT_CA_PATH`, `BANKID_TEST_CHECK_IP` | The test environment, see the table above. Script 02 and the Bicep set the vault address from the test vault, and the certificate name to `fptestcert5` |
| `BANKID_PRODUCTION_URL`, `BANKID_PRODUCTION_KEYVAULT_URI`, `BANKID_PRODUCTION_CERTIFICATE_NAME`, `BANKID_PRODUCTION_ROOT_CA_PATH`, `BANKID_PRODUCTION_CHECK_IP` | The production environment |

**The scripts** read the Backend API variables above (script 02 passes them to the Bicep), plus these:

| Variable | Used by | Meaning |
|----------|---------|---------|
| `RECIPE_PREFIX` | 01 to 05 | A unique prefix for this recipe, such as `thunderbirdsarego`, that names every resource. You set it, see below |

**Every name is built from `RECIPE_PREFIX`, the prefix of this recipe. It is not the tenant, and it works like `TENANT_PREFIX` in the Use An Azure Web App recipe.** Many Azure names must be globally unique, so you choose a prefix once, for example `$env:RECIPE_PREFIX = 'thunderbirdsarego'`, and the scripts build the names:

| Resource | Name |
|----------|------|
| Resource group | `<prefix>-rg1` |
| Test Key Vault | `<first 15 letters and digits of the prefix>-bid-test` (a vault name is at most 24 characters) |
| Production Key Vault | `<first 15 letters and digits of the prefix>-bid-prod` |
| App Service plan | `<prefix>-plan` |
| Backend API | `<prefix>-api`, which becomes `https://<prefix>-api.azurewebsites.net` |
| Web site | `<prefix>-web`, which becomes `https://<prefix>-web.azurewebsites.net` |

These are the same names the Foundry recipe builds, so use a different prefix for each recipe if you deploy both. Each script also takes parameters (`-ResourceGroup`, `-TestKeyVaultName`, `-ProductionKeyVaultName`, `-PlanName`, `-BackendName`, `-WebAppName`) if you want to choose a name yourself.

**You create the resource group by hand**, in the Azure portal or with `az group create -n <prefix>-rg1 -l <region>`. The scripts never create or change it. They stop with a message if it doesn't exist. Everything is created in the region of that group. The tenant and subscription are never set: they are the ones `az` is signed in to, and the resources are created there. If you have several subscriptions, select one first with `az account set --subscription <name>`.

There is no variable for a certificate file or its password. Neither certificate goes through a script, a Bicep file or an environment variable, see [Upload the certificates by hand](#upload-the-certificates-by-hand).

## Deploy to Azure

You need the Azure CLI (`az login`), PowerShell and the .NET 10 SDK. Set the variables, then run the scripts in order:

```
az login
$env:RECIPE_PREFIX = 'thunderbirdsarego'                # names everything, see above
az group create -n "$env:RECIPE_PREFIX-rg1" -l <region>   # you create the resource group by hand
./azure/01_create-keyvault.ps1                           # the test and production Key Vaults in your resource group

# upload the test and the production certificate to their vaults by hand, see "Upload the certificates by hand" below.
# They are only needed when you use the web site, so you can do it before or after the scripts below.

# the rest of the Backend API variables, see the tables above
./azure/02_create-backendapi.ps1                         # App Service plan and Backend API, application settings, Key Vault Secrets User roles
./azure/03_deploy-backendapi.ps1                         # publishes the Backend API and deploys it
./azure/04_create-webapp.ps1                             # the web site, with BACKEND_API_URL
./azure/05_deploy-webapp.ps1                             # publishes the web site and deploys it
```

1. `01_create-keyvault.ps1` creates two vaults, one for test and one for production, with Azure role based access, soft delete and purge protection. A deleted certificate cannot be purged for 90 days. You get the Key Vault Certificates Officer role on both, so you can upload
2. `02_create-backendapi.ps1` creates the App Service plan and the Backend API (Linux, .NET 10, https only) with a system assigned identity, and gives that identity the Key Vault Secrets User role on both vaults. The Backend API reads the certificates with that identity. There is no password or key in the application settings
3. `03_deploy-backendapi.ps1` runs `dotnet publish` on `backendapi` and deploys the zip
4. `04_create-webapp.ps1` creates the web site on the same plan, with `BACKEND_API_URL` set to the Backend API
5. `05_deploy-webapp.ps1` runs `dotnet publish` on `website` and deploys the zip

Role assignments can take a few minutes to take effect. Then open the web site address that script 04 prints. Settings that Bicep creates are replaced every time you run the script again, so change a value by setting the variable and running the script, not by editing it in the portal.

## On localhost the sign in is fake

The solution works in Azure only. The real sign in needs the Backend API, the Key Vault certificates and BankID, and those are in Azure. If you open the web site on `localhost` (for example `dotnet run` in `website` on your PC) there is no Backend API to call, so the web site answers the sign in calls itself and **shows a banner: "Fake sign in: this page is running on localhost, so nothing is sent to BankID. The real sign in only works in Azure."**

- The test or production option, the QR code (a placeholder), the waiting messages and the signed in view all work
- The user it signs in is made up: **Fake User**, personal number `199001019999`
- Nothing is sent to BankID, and no Azure, certificate or BankID is needed
- It is decided by the address in the browser: `localhost`, `127.0.0.1` or `::1`. In Azure the fake calls answer "not found", so it cannot be used there

```
cd website
dotnet run
```

The Backend API does not run locally. It would need your Key Vault certificates and, for the production option, a page from the Azure web site.

## Upload the certificates by hand

No script and no Bicep file deploys a certificate, and no environment variable holds one or its password. `01_create-keyvault.ps1` creates the two empty vaults and gives you the Key Vault Certificates Officer role on both, and you put the certificates in yourself. Bicep cannot do it: it can only create a plain secret in Key Vault, not import a PKCS#12 (`.p12` or `.pfx`) certificate. Key Vault's own import also removes the file's password, which is what the Backend API relies on when it loads the certificate.

The steps in the Azure portal are the same for both certificates. Open the Key Vault, go to **Objects → Certificates → Generate/Import**, set **Method of Certificate Creation** to **Import**, enter the certificate name, upload the file, enter its password and select **Create**. Anyone other than the person who ran script 01 needs the Key Vault Certificates Officer role on the vault, under **Access control (IAM)**.

**The test certificate, into the test vault.** BankID publishes it for everyone, so there is nothing secret about it:
1. Download the zip from the [BankID test portal](https://developers.bankid.com/test-portal/test-information) and unzip it. Use `FPTestcert5_20240610.p12`. If Key Vault refuses it, use the legacy `.pfx` from the same zip
2. Open the **test** Key Vault (`<prefix, 15 characters>-bid-test`)
3. Use the certificate name **`fptestcert5`**. Script 02 gives the Backend API exactly this name, so it must match
4. The password is **`qwerty123`**. BankID publishes it, in the README inside the zip and on its test page. It only works against BankID's test servers

**The production certificate, into the production vault.** It is the secret that proves your organisation to BankID. It comes from your bank, and BankID says it must be requested from the bank you have an agreement with:
1. Get the certificate from your bank. You create the request with BankID's Keygen tool and your bank returns the signed certificate, and Keygen builds the PKCS#12 file. See [Request a certificate](https://developers.bankid.com/getting-started/order-certificate/request-a-certificate). The password is the one you chose
2. Open the **production** Key Vault (`<prefix, 15 characters>-bid-prod`)
3. Use the certificate name you gave script 02 in `BANKID_PRODUCTION_CERTIFICATE_NAME`, for example `bankid-production-certificate`
4. Upload the file and enter the password you chose

Then open the web site and choose **Test** or **Production**. The Backend API reads each certificate the first time that environment is used. If it was used before the certificate existed, the next attempt tries again. When a certificate is renewed, upload the new file under the same name, which adds a new version, and restart the Backend API so that it loads it. Delete the file from your PC when you have uploaded it, and keep the production password in your password manager, not in a script.

BankID's [Environments](https://developers.bankid.com/getting-started/environments) page describes the two environments and states that test and production use different certificates. A test certificate cannot be used against production.

## Test it

1. Get a Test BankID. Configure the BankID app for test and issue a Test BankID, see the [BankID test portal](https://developers.bankid.com/test-portal/bankid-for-test). Use a spare phone or the desktop BankID Security Application, because an app configured for test cannot be used for real sign ins. Check it works by logging in at https://demo.bankid.com using "Log in with a Test BankID"
2. Open the web site address and choose **Test**
3. On a PC select **BankID On Another Device** and scan the QR code. On a phone select **BankID On This Device**

If something goes wrong the web site shows the message from the Backend API, for example that the certificate is not in Key Vault yet.

## Requirements for production

1. An agreement with a bank that sells BankID
2. A relying party certificate ordered from that bank. It is not the test certificate
3. The certificate uploaded by hand to the production Azure Key Vault and read by the Backend API with its managed identity (never in the web site, in a script or in source control)
4. The BankID SSL root CA for production in the Backend API trust store (`certs/BankID-SSL-Root-CA-v1.pem`)
5. Calls to `https://appapi2.bankid.com/rp/v6.0/` over TLS 1.2 or 1.3 with the certificate
6. The real end user ip sent in every order (`endUserIp`), and a check that it matches the `ip` in the `/collect` result (`CheckIp`)
7. The `qrStartSecret` kept in the Backend API, and `/collect` called every 2 seconds
8. The certificate renewed before it expires

Also for production: serve the web site on your own https domain and give `02_create-backendapi.ps1` that address with `-WebSiteUrl`, replace the in-memory orders and sessions in `Program.cs` with a shared cache if you run more than one instance, and follow BankID's guidelines for texts and graphics.

## Docs

- BankID developer site: https://developers.bankid.com
