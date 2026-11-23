# Publishes ../website and deploys it to the Web App created by 12_create-webapp.ps1.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$WebAppName = "${env:TENANT_PREFIX}-web"
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
$website = Join-Path $PSScriptRoot '..\website'
$publish = Join-Path ([System.IO.Path]::GetTempPath()) 'website-publish'
$zip = "$publish.zip"

if (Test-Path $publish) { Remove-Item $publish -Recurse -Force }
if (Test-Path $zip) { Remove-Item $zip -Force }
dotnet publish $website -c Release -o $publish
if ($LASTEXITCODE -ne 0) { throw 'dotnet publish failed.' }

# Not Compress-Archive or ZipFile.CreateFromDirectory: in Windows PowerShell 5.1 both write backslashes in entry
# names, which a Linux App Service treats as part of the file name and fails to extract.
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
az webapp deploy -g $ResourceGroup -n $WebAppName --src-path $zip --type zip
if ($LASTEXITCODE -ne 0) { throw 'Deployment failed.' }

"Deployed. Open https://$WebAppName.azurewebsites.net"
