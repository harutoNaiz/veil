# Verify sub-phase 5.3.3 "Battery, chapter report, twin sync, proof-test driver". No Gradle.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $good = ($LASTEXITCODE -eq 0)
  if (-not $good) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($good) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $good) { $script:failed = $true }
}
$files = 'workshop/perf/battery workshop/perf/report.py workshop/perf/tune.py workshop/perf/tests'.Split(' ')
Check '(1) pytest battery + report/tune' { uv run --locked pytest workshop/perf/battery workshop/perf/tests -q }
Check '(2) tune --check' { uv run --locked python -m workshop.perf.tune --check }
Check '(3) twin tapes' { uv run --locked pytest workshop/replay -q }
Check '(4) report empty dir -> PENDING-HUMAN' {
  $d = Join-Path $env:TEMP 'veil-533-empty'; New-Item -ItemType Directory -Force $d | Out-Null
  uv run --locked python -m workshop.perf.report --evidence $d --out "$d\r.md"
  if ($LASTEXITCODE -eq 0) { if (-not (Select-String -Path "$d\r.md" -Pattern 'PENDING-HUMAN' -Quiet)) { cmd /c exit 1 } }
}
Check '(5) session no device -> exit 2' {
  uv run --locked python -m workshop.perf.battery.session --minutes 0 --runs "$env:TEMP\veil-533-runs.json"
  if ($LASTEXITCODE -eq 2) { cmd /c exit 0 } else { cmd /c exit 1 }
}
Check '(6) ruff' {
  uv run --locked ruff check $files
  if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check $files }
}
if ($script:failed) { Write-Host 'VERIFY 5.3.3: FAIL'; exit 1 }
Write-Host 'VERIFY 5.3.3: PASS'
