# Copies ../website (plain HTML and JavaScript, nothing to build), writes the Backend API address into config.json,
# and deploys it to the web site App Service created by 05_create-webapp.ps1.
param(
  [string]$ResourceGroup = "${env:RECEIPE_PREFIX}-bankid-rg",
  [string]$WebAppName = "${env:RECEIPE_PREFIX}-bankid-web",
  [string]$BackendName = "${env:RECEIPE_PREFIX}-bankid-api"
)
if (-not $env:RECEIPE_PREFIX) { throw 'Set the RECEIPE_PREFIX environment variable first, for example:  $env:RECEIPE_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
$site = Join-Path $PSScriptRoot '..\website'
$stage = Join-Path ([System.IO.Path]::GetTempPath()) 'bankid-website-stage'
$zip = "$stage.zip"

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
if (Test-Path $zip) { Remove-Item $zip -Force }
Copy-Item $site $stage -Recurse

# The only deployment specific setting: where the page finds the Backend API.
@{ backendUrl = "https://$BackendName.azurewebsites.net" } | ConvertTo-Json | Set-Content (Join-Path $stage 'config.json') -Encoding utf8

# Not Compress-Archive: in Windows PowerShell 5.1 it writes backslashes in entry names, which a Linux App Service
# treats as part of the file name. So the entries are added one by one with forward slashes.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($zip, 'Create')
try {
  $root = (Resolve-Path $stage).Path.TrimEnd('\') + '\'
  foreach ($file in Get-ChildItem $stage -Recurse -File) {
    [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $file.FullName.Substring($root.Length).Replace('\', '/'))
  }
} finally { $archive.Dispose() }

az webapp deploy -g $ResourceGroup -n $WebAppName --src-path $zip --type zip
if ($LASTEXITCODE -ne 0) { throw 'Deployment failed.' }
"Deployed the web site: https://$WebAppName.azurewebsites.net"
