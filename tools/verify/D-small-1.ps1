# Verify D-small-1 (pt-4.2 driver + tune main-assets check). Ends with VERIFY D-small-1: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
function Check([string]$name, [scriptblock]$body, [int]$want = 0) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq $want)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}
$pt = "$repo\tools\verify\pt-4.2.ps1"
$py = @('workshop/perf/tune.py', 'workshop/perf/tests/test_report_tune.py')
Check 'parse pt-4.2.ps1' {
  $e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile($pt, [ref]$null, [ref]$e)
  $global:LASTEXITCODE = [int]($e.Count -gt 0)
}
Check 'pt-4.2 -DryRun exits 0' { powershell -NoProfile -ExecutionPolicy Bypass -File $pt -DryRun }
Check 'pt-4.2 no device exits 2' { powershell -NoProfile -ExecutionPolicy Bypass -File $pt } 2
Check 'tune --check' { uv run --locked python -m workshop.perf.tune --check }
Check 'pytest perf' { uv run --locked pytest workshop/perf/tests -q }
Check 'ruff check' { uv run --locked ruff check @py }
Check 'ruff format' { uv run --locked ruff format --check @py }
if ($script:failed) { Write-Host 'VERIFY D-small-1: FAIL'; exit 1 }
Write-Host 'VERIFY D-small-1: PASS'
