# Verify sub-phase 2.1.3 "Replay harness and tape v1". Run from anywhere:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\2.1.3.ps1
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

Step '1 pytest workshop/replay' { uv run pytest workshop/replay -q }
Step '2 pytest contracts' { uv run pytest contracts -q }
Step '3 valid tape examples validate' { uv run python -m workshop.replay.tape validate contracts/examples-tape/valid-01-header.jsonl contracts/examples-tape/valid-02-frame.jsonl }
Step '4 invalid tape examples fail' { uv run python -m workshop.replay.tape validate contracts/examples-tape/invalid-01-header-version.jsonl } 1
Step '5 ruff format check' { uv run ruff format --check workshop/replay }
Step '6 ruff check (project config)' { uv run --locked ruff check workshop/replay contracts/tests/test_schemas.py }

if ($script:failed) { Write-Host 'VERIFY 2.1.3: FAIL'; exit 1 }
Write-Host 'VERIFY 2.1.3: PASS'
