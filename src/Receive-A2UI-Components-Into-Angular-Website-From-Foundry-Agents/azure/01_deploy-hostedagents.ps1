# Deploys the two A2UI recipe hosted agents (a2ui-response and a2ui-stream) from source. No container, no registry.
# It zips each agent folder, then runs create_hostedagents.bicep, which uploads the zips to Foundry and waits until each
# agent is active. Run 02_create-hostedagentroles.ps1 next.
#
# Needs: az login, the Foundry resource and project (the names below match the other recipe's TENANT_PREFIX convention),
# and Foundry public access still on. Run it again after changing an agent: Foundry adds a new version.
param(
  [string]$ResourceGroup = "${env:TENANT_PREFIX}-rg1",
  [string]$FoundryName = "${env:TENANT_PREFIX}",
  [string]$ProjectName = "${env:TENANT_PREFIX}-FoundryProject",
  [string]$ModelDeployment = 'gpt-4.1-mini'
)
if (-not $env:TENANT_PREFIX) { throw 'Set the TENANT_PREFIX environment variable first, for example:  $env:TENANT_PREFIX = ''your-tenant-prefix''' }
$ErrorActionPreference = 'Stop'

# Agents to deploy. The name is also the folder under ..\hostedagents and the assembly name.
# protocols: what the agent returns its data over. a2ui-response answers over the Responses protocol. a2ui-stream serves
# AG-UI, which Foundry has no protocol for, so it registers the Invocations protocol and streams AG-UI events as raw SSE.
# Both use protocol version 2.0.0, the version the Foundry docs show for hosted agents.
$sources = @(
  @{ name = 'a2ui-response'; description = 'Answers a question with one complete plain text answer.'
     protocols = @(@{ protocol = 'responses'; version = '2.0.0' }) },
  @{ name = 'a2ui-stream';   description = 'Answers a question as a stream of AG-UI text events.'
     protocols = @(@{ protocol = 'invocations'; version = '2.0.0' }) }
)

Add-Type -AssemblyName System.IO.Compression.FileSystem
$agents = @()
foreach ($s in $sources) {
  $folder = Join-Path $PSScriptRoot "..\hostedagents\$($s.name)"
  if (-not (Test-Path $folder)) { throw "Missing agent folder $folder" }

  # Zip the project sources only, flat at the root: no bin, obj or publish output. Foundry runs dotnet restore and publish.
  $tmp = Join-Path ([IO.Path]::GetTempPath()) "$($s.name)-src"
  if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
  New-Item -ItemType Directory $tmp | Out-Null
  Get-ChildItem $folder -File | Where-Object { $_.Extension -in '.csproj', '.cs' } | Copy-Item -Destination $tmp
  $zip = Join-Path ([IO.Path]::GetTempPath()) "$($s.name).zip"
  if (Test-Path $zip) { Remove-Item $zip -Force }
  [IO.Compression.ZipFile]::CreateFromDirectory($tmp, $zip)

  $agents += @{
    name        = $s.name
    entryDll    = "$($s.name).dll"      # the .csproj name is the assembly name
    description = $s.description
    protocolVersions = @($s.protocols)
    sha256      = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
    zipBase64   = [Convert]::ToBase64String([IO.File]::ReadAllBytes($zip))
  }
  "Zipped $($s.name): $([math]::Round((Get-Item $zip).Length / 1KB, 1)) KB"
}

# The agents parameter goes in a file: it holds the zips, which are too long for the command line.
$paramFile = Join-Path ([IO.Path]::GetTempPath()) 'a2ui-hostedagents.parameters.json'
@{
  '$schema'      = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'
  contentVersion = '1.0.0.0'
  parameters     = @{ agents = @{ value = @($agents) } }
} | ConvertTo-Json -Depth 10 | Set-Content $paramFile -Encoding utf8

# deploymentScripts needs this provider (it runs in an Azure Container Instance).
az provider register --namespace Microsoft.ContainerInstance --wait

$out = az deployment group create -g $ResourceGroup `
  -f "$PSScriptRoot/create_hostedagents.bicep" `
  -p "@$paramFile" foundryName=$FoundryName projectName=$ProjectName modelDeployment=$ModelDeployment `
  --query properties.outputs -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Hosted agent deployment failed.' }

"Deployed hosted agents: $($out.agentNames.value -join ', ')"
"Next: run 02_create-hostedagentroles.ps1"
