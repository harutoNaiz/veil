# Verify sub-phase 5.3.1 "Time to cover".
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\5.3.1.ps1
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Step([string]$name, [scriptblock]$body, [int]$expect = 0) {
  & $body | Out-Host
  $code = $LASTEXITCODE
  if ($code -eq $expect) { Write-Host "ok    $name" }
  else { Write-Host "FAIL  $name (exit $code, wanted $expect)"; $script:failed = $true }
}

$p = 'workshop/perf/latency'
Step '0 ruff' { uv run --locked ruff check $p workshop/perf/schema.py workshop/perf/__init__.py; if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check $p workshop/perf/schema.py workshop/perf/__init__.py } }
Step '1 pytest' { uv run --locked pytest workshop/perf/latency -q }
Step '2 regenerate fixtures' { uv run --locked python -m workshop.perf.latency.tests.gen }
$out = Join-Path $env:TEMP 'veil-latency.json'
$line = uv run --locked python -m workshop.perf.latency.parse --debug "$p/tests/fixtures/debug.jsonl" --feed "$p/tests/fixtures/feedlog.jsonl" --out $out | Select-Object -Last 1
Write-Host $line
if ($line -match '^P95 213 n=120 ') { Write-Host 'ok    3 CLI P95' } else { Write-Host 'FAIL  3 CLI P95'; $script:failed = $true }
Step '4 capture no device exits 2' { $env:ADB = 'veil-no-such-adb'; uv run --locked python -m workshop.perf.latency.capture --minutes 1; Remove-Item Env:ADB } 2
if ($script:failed) { Write-Host 'VERIFY 5.3.1: FAIL'; exit 1 } else { Write-Host 'VERIFY 5.3.1: PASS' }
