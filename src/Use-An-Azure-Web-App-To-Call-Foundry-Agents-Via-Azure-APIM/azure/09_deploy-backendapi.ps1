# Publishes ../backendapi and deploys it to the Backend API App Service created by 07_create-backendapi.ps1.
# The site itself only accepts calls from API Management, but deployment goes through the separate SCM site, so this
# works from your PC.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$BackendName = "${env:TENANT_PREFIX}-api"
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
$backendapi = Join-Path $PSScriptRoot '..\backendapi'
$publish = Join-Path ([System.IO.Path]::GetTempPath()) 'backendapi-publish'
$zip = "$publish.zip"

if (Test-Path $publish) { Remove-Item $publish -Recurse -Force }
if (Test-Path $zip) { Remove-Item $zip -Force }
dotnet publish $backendapi -c Release -o $publish
if ($LASTEXITCODE -ne 0) { throw 'dotnet publish failed.' }

# Not Compress-Archive or ZipFile.CreateFromDirectory: in Windows PowerShell 5.1 both write backslashes in entry
# names (runtimes\win\...), which a Linux App Service treats as part of the file name and fails to extract.
# So the entries are added one by one with forward-slash names.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($zip, 'Create')
try {
  $root = (Resolve-Path $publish).Path.TrimEnd('\') + '\'
  foreach ($file in Get-ChildItem $publish -Recurse -File) {
    $entryName = $file.FullName.Substring($root.Length).Replace('\', '/')
    [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $entryName)
  }
} finally { $archive.Dispose() }
az webapp deploy -g $ResourceGroup -n $BackendName --src-path $zip --type zip
if ($LASTEXITCODE -ne 0) { throw 'Deployment failed.' }

"Deployed the Backend API to $BackendName (reachable only through API Management)."
