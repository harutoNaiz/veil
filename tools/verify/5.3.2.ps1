# Verify sub-phase 5.3.2 "Smoothness, memory, heat, kills".
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\5.3.2.ps1
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

$fx = 'workshop/perf/smooth/tests/fixtures'
$tmp = Join-Path $env:TEMP 'veil532'
New-Item -ItemType Directory -Force $tmp | Out-Null
Step '1 pytest' { uv run --locked python -m pytest workshop/perf/smooth -q }
Step '2 section PASS' { uv run --locked python -m workshop.perf.smooth.section --dir $fx --out "$tmp/p.json" }
if ((Get-Content "$tmp/p.json" -Raw) -match '"status": "PASS"') { Write-Host 'ok    2b status PASS' } else { Write-Host 'FAIL  2b status not PASS'; $script:failed = $true }
Step '3 section fail dir' { uv run --locked python -m workshop.perf.smooth.section --dir "$fx/fail" --out "$tmp/f.json" }
if ((Get-Content "$tmp/f.json" -Raw) -match '"status": "FAIL"') { Write-Host 'ok    3b status FAIL' } else { Write-Host 'FAIL  3b status not FAIL'; $script:failed = $true }
Step '4 sample no device' { uv run --locked python -m workshop.perf.smooth.sample --serial NONE } 2
Step '5 kill no device' { uv run --locked python -m workshop.perf.smooth.kill --serial NONE } 2
Step '6 ruff' { uv run --locked ruff check workshop/perf/smooth; if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check workshop/perf/smooth } }

if ($script:failed) { Write-Host 'VERIFY 5.3.2: FAIL'; exit 1 }
Write-Host 'VERIFY 5.3.2: PASS'
