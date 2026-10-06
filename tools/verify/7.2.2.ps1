# Verify sub-phase 7.2.2 "Evaluate, attempts log, report, no-per-word check".
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\7.2.2.ps1
# Loads no model (synthetic bench, stub judge).
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

$py = @('workshop/twin/bench/evaluate.py', 'workshop/twin/bench/attempts.py', 'workshop/twin/bench/word_params_check.py', 'workshop/twin/bench/tests/test_bench_eval.py')
Step '1 ruff check' { uv run --locked ruff check @py }
Step '2 ruff format --check' { uv run --locked ruff format --check --line-length 100 @py }
Step '3 pytest bench eval' { uv run --locked pytest workshop/twin/bench/tests/test_bench_eval.py -q }
Step '4 no per-word params' { uv run --locked python -m workshop.twin.bench.word_params_check }

if ($script:failed) { Write-Host 'VERIFY 7.2.2: FAIL'; exit 1 }
Write-Host 'VERIFY 7.2.2: PASS'
