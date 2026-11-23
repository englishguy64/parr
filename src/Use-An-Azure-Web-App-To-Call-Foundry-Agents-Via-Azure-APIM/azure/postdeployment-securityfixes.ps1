# Tightens security settings on the Backend API and the website (TLS 1.2, no FTP, no SCM basic auth, HTTP/2).
# Run it last, after 09_deploy-backendapi.ps1 and 13_deploy-website.ps1. Re-deploying code afterwards works with
# 'az webapp deploy' because it signs in with Entra ID. Pass -KeepScmBasicAuth if you need the SCM publishing password.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$BackendName = "${env:TENANT_PREFIX}-api",
  [string]$WebAppName = "${env:TENANT_PREFIX}-web",
  [switch]$KeepScmBasicAuth
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'

az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/postdeployment-securityfixes.bicep" `
  -p backendName=$BackendName webAppName=$WebAppName disableScmBasicAuth=$((-not $KeepScmBasicAuth).ToString().ToLower()) `
  -o none
if ($LASTEXITCODE -ne 0) { throw 'Security fixes deployment failed.' }

# Show what is now set, and that the app kept its VNet integration and access restrictions.
foreach ($app in @($BackendName, $WebAppName)) {
  "--- $app"
  az webapp config show -g $ResourceGroup -n $app `
    --query "{minTls:minTlsVersion, scmMinTls:scmMinTlsVersion, ftps:ftpsState, http20:http20Enabled, runtime:linuxFxVersion, restrictions:length(ipSecurityRestrictions)}" -o json
}
"Done. If a restriction count or runtime above looks wrong, tell me before redeploying anything."
