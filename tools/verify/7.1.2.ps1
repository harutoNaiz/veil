# Verify sub-phase 7.1.2 "Auto threshold, competitors, ensembles (twin)".
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\7.1.2.ps1
# Loads no real model. The full eval (needs the heavy bank) is run by the orchestrator, alone:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 uv run --locked python -m workshop.twin.autocal_eval --bank data/bank/v1
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

$py = @('workshop/twin/autocal.py', 'workshop/twin/autocal_eval.py', 'workshop/twin/judge.py', 'workshop/twin/tests/test_autocal.py', 'workshop/twin/tests/fixtures/autocal/make.py')
Step '1 ruff check' { uv run --locked ruff check @py }
Step '2 ruff format --check' { uv run --locked ruff format --check --line-length 100 @py }
Step '3 pytest autocal' { uv run --locked pytest workshop/twin/tests/test_autocal.py -q }
Step '4 pytest twin v0 + motion' { uv run --locked pytest workshop/twin/tests/test_twin_v0.py workshop/twin/tests/test_motion.py -q }
Step '5 pytest contracts' { uv run --locked pytest contracts/tests -q }

if ($script:failed) { Write-Host 'VERIFY 7.1.2: FAIL'; exit 1 }
Write-Host 'VERIFY 7.1.2: PASS'
