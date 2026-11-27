# Deletes everything this receipe created. The Key Vault has purge protection, so its name stays reserved for 7 days.
param(
  [string]$ResourceGroup = "${env:RECEIPE_PREFIX}-bankid-rg"
)
if (-not $env:RECEIPE_PREFIX) { throw 'Set the RECEIPE_PREFIX environment variable first, for example:  $env:RECEIPE_PREFIX = ''thundersbirdsarego64''' }
$ErrorActionPreference = 'Stop'
az group delete -n $ResourceGroup --yes --no-wait
"Deleting $ResourceGroup (runs in the background)."
