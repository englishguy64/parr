# Publishes the web site (the code in ../website) and deploys it to the web site App Service created by the script before this one.
# Every setting is an environment variable and none has a default.
#
#   RECIPE_PREFIX   names the resource group and the web site, as in 02_create-backendapi.ps1
param(
  [string]$ResourceGroup = "${env:RECIPE_PREFIX}-rg1",
  [string]$WebAppName = "${env:RECIPE_PREFIX}-web"
)
$ErrorActionPreference = 'Stop'
if (-not $env:RECIPE_PREFIX) { throw 'Set the RECIPE_PREFIX environment variable first, for example:  $env:RECIPE_PREFIX = ''thunderbirdsarego''' }

if ((az group exists -n $ResourceGroup) -ne 'true') { throw "Resource group $ResourceGroup does not exist." }

$project = Join-Path $PSScriptRoot '..\website\website.csproj'
$publish = Join-Path ([System.IO.Path]::GetTempPath()) 'bankid-website-publish'
$zip = "$publish.zip"

if (Test-Path $publish) { Remove-Item $publish -Recurse -Force }
if (Test-Path $zip) { Remove-Item $zip -Force }

dotnet publish $project -c Release -o $publish
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

az webapp deploy -g $ResourceGroup -n $WebAppName --src-path $zip --type zip
if ($LASTEXITCODE -ne 0) { throw 'Deployment failed.' }

$address = az webapp show -g $ResourceGroup -n $WebAppName --query defaultHostName -o tsv
"Deployed the web site. Address: https://$address/"
