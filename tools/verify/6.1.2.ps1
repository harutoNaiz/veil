# Verify sub-phase 6.1.2 "Onboarding and permissions" (flutter analyze + test).
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
$w = Join-Path $repo 'tools\with-env.ps1'

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

Check '(1) flutter analyze' {
  powershell -NoProfile -ExecutionPolicy Bypass -File $w --cd console flutter analyze lib/main.dart lib/app.dart lib/theme.dart lib/onboarding lib/status test/onboarding test/widget_test.dart
}
Check '(2) flutter test' {
  powershell -NoProfile -ExecutionPolicy Bypass -File $w --cd console flutter test test/onboarding test/widget_test.dart
}

if ($script:failed) { Write-Host 'VERIFY 6.1.2: FAIL'; exit 1 }
Write-Host 'VERIFY 6.1.2: PASS'
