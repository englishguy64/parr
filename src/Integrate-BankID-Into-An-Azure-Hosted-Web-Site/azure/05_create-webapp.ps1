# Creates the web site App Service on the plan made by 03_create-backendapi.ps1. Deploy the code with 06_deploy-webapp.ps1 next.
param(
  [string]$ResourceGroup = "${env:RECEIPE_PREFIX}-bankid-rg",
  [string]$WebAppName = "${env:RECEIPE_PREFIX}-bankid-web",
  [string]$PlanName = "${env:RECEIPE_PREFIX}-bankid-plan",
  [string]$Location = 'germanywestcentral',
  [switch]$PreviewOnly
)
if (-not $env:RECEIPE_PREFIX) { throw 'Set the RECEIPE_PREFIX environment variable first, for example:  $env:RECEIPE_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'

$template = @('-g', $ResourceGroup, '-f', "$PSScriptRoot/create_webapp.bicep", '-p',
  "webAppName=$WebAppName", "appServicePlanName=$PlanName", "location=$Location")
if ($PreviewOnly) { az deployment group what-if @template; return }

$out = az deployment group create @template --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Web site deployment failed.' }
"WEB_URL=$($out.webUrl.value)   (next: 06_deploy-webapp.ps1)"
