# Publishes ../backendapi and deploys it to the Backend API App Service created by 03_create-backendapi.ps1.
param(
  [string]$ResourceGroup = "${env:RECEIPE_PREFIX}-bankid-rg",
  [string]$BackendName = "${env:RECEIPE_PREFIX}-bankid-api"
)
if (-not $env:RECEIPE_PREFIX) { throw 'Set the RECEIPE_PREFIX environment variable first, for example:  $env:RECEIPE_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
$project = Join-Path $PSScriptRoot '..\backendapi'
$publish = Join-Path ([System.IO.Path]::GetTempPath()) 'bankid-backendapi-publish'
$zip = "$publish.zip"

if (Test-Path $publish) { Remove-Item $publish -Recurse -Force }
if (Test-Path $zip) { Remove-Item $zip -Force }
dotnet publish $project -c Release -o $publish
if ($LASTEXITCODE -ne 0) { throw 'dotnet publish failed.' }

# Not Compress-Archive: in Windows PowerShell 5.1 it writes backslashes in entry names, which a Linux App Service
# treats as part of the file name. So the entries are added one by one with forward slashes.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($zip, 'Create')
try {
  $root = (Resolve-Path $publish).Path.TrimEnd('\') + '\'
  foreach ($file in Get-ChildItem $publish -Recurse -File) {
    [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $file.FullName.Substring($root.Length).Replace('\', '/'))
  }
} finally { $archive.Dispose() }

az webapp deploy -g $ResourceGroup -n $BackendName --src-path $zip --type zip
if ($LASTEXITCODE -ne 0) { throw 'Deployment failed.' }
"Deployed the Backend API. Check https://$BackendName.azurewebsites.net/api/health"
