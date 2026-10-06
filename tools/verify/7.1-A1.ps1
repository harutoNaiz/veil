# Verify Amendment A1 (null-quantile-v2). Re-runs 7.1.1-7.1.3 plus the v2 tests.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false
foreach ($s in '7.1.1', '7.1.2', '7.1.3') {
  $out = @(& powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\$s.ps1" 2>&1 | ForEach-Object { "$_" })
  if ($out -match "VERIFY ${s}: PASS") { Write-Host "ok    $s" }
  else { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" }; Write-Host "FAIL  $s"; $failed = $true }
}
uv run --locked pytest workshop/twin/tests/test_autocal.py -q -k "v2 or kite or center" | Out-Host
if ($LASTEXITCODE -ne 0) { Write-Host 'FAIL  v2 tests'; $failed = $true } else { Write-Host 'ok    v2 tests' }
if ($failed) { Write-Host 'VERIFY 7.1-A1: FAIL'; exit 1 }
Write-Host 'VERIFY 7.1-A1: PASS'
