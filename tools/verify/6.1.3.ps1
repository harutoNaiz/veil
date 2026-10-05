# Verify sub-phase 6.1.3 "Main screens" (flutter analyze + flutter test only).
$env:VEIL_ENV_QUIET = '1'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 30 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}
$we = "$repo\tools\with-env.ps1"
Check '(1) flutter analyze lib/screens test/screens' {
  powershell -NoProfile -ExecutionPolicy Bypass -File $we --cd console flutter analyze lib/screens test/screens
}
Check '(2) flutter test test/screens' {
  powershell -NoProfile -ExecutionPolicy Bypass -File $we --cd console flutter test test/screens
}
if ($script:failed) { Write-Host 'VERIFY 6.1.3: FAIL'; exit 1 }
Write-Host 'VERIFY 6.1.3: PASS'
