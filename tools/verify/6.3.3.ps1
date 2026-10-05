# Verify sub-phase 6.3.3 "Demo and pitch".
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

function Run([string[]]$cmd) { powershell -NoProfile -ExecutionPolicy Bypass -File $w @cmd }

Check '(1) ruff' {
  Run @('uv', 'run', '--locked', 'ruff', 'check', 'workshop/demo')
  if ($LASTEXITCODE -eq 0) { Run @('uv', 'run', '--locked', 'ruff', 'format', '--check', 'workshop/demo') }
}
Check '(2) pytest' { Run @('uv', 'run', '--locked', 'pytest', 'workshop/demo/tests', '-q') }
$real = Join-Path $repo 'docs\reports\final.md'
$report = if (Test-Path $real) { $real } else { Join-Path $repo 'workshop\demo\tests\fixture_final.md' }
Write-Host "    using report: $report"
Check '(3) trace_claims' {
  Run @('uv', 'run', '--locked', 'python', '-m', 'workshop.demo.trace_claims', '--docs', 'docs/demo', '--report', $report, '--appendix-c')
}

if ($script:failed) { Write-Host 'VERIFY 6.3.3: FAIL'; exit 1 }
Write-Host 'VERIFY 6.3.3: PASS'
