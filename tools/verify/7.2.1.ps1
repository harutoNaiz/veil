# Verify sub-phase 7.2.1 "Frozen benchmark".
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\7.2.1.ps1
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Step([string]$name, [scriptblock]$body) {
  & $body | Out-Host
  if ($LASTEXITCODE -eq 0) { Write-Host "ok    $name" }
  else { Write-Host "FAIL  $name (exit $LASTEXITCODE)"; $script:failed = $true }
}

$b = 'workshop/twin/bench'
$files = @("$b/fmt.py", "$b/oi.py", "$b/select.py", "$b/compose.py", "$b/fetch_embed.py", "$b/disjoint.py", "$b/tests/test_bench_data.py")
Step '0 ruff' { uv run --locked ruff check @files; if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check @files } }
Step '1 pytest' { uv run --locked pytest workshop/twin/bench/tests/test_bench_data.py -q }
Step '2 select --smoke' { uv run --locked python -m workshop.twin.bench.select --out data/bench/smoke --smoke }

if ($script:failed) { Write-Host 'VERIFY 7.2.1: FAIL'; exit 1 }
Write-Host 'VERIFY 7.2.1: PASS'
