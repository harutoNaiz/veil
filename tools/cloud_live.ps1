# Live cloud-phone run (HC-003: needs AI Hub token). Stops on first error. Never run by verify.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\env.ps1"
Set-Location (Split-Path -Parent $PSScriptRoot)
$ErrorActionPreference = 'Continue'
$steps = @(
  @('profile', '--live'), @('precision', '--live'), @('budget', '--live'),
  @('manifests', '--live'), @('manifests', '--check', 'workshop/forge/manifests'), @('report')
)
foreach ($s in $steps) {
  Write-Host ">> $($s -join ' ')"
  $rest = @($s | Select-Object -Skip 1)
  uv run --locked python -m "workshop.forge.cloud.$($s[0])" @rest
  if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $($s -join ' ')"; exit $LASTEXITCODE }
}
Write-Host 'cloud_live: done'
