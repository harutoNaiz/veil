# Verify sub-phase 7.1.1 "Reference bank".
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\7.1.1.ps1
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

Step '0 ruff' { uv run --locked ruff check workshop/twin/bank; if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check workshop/twin/bank } }
Step '1 pytest' { uv run --locked pytest workshop/twin/bank/tests -q }
if (-not (Test-Path 'data\bank\smoke\bank.bin')) {
  Step '2 build smoke' { uv run --locked python -m workshop.twin.bank.build_bank --out data/bank/smoke --limit 200 --ui 20 --vocab-limit 100 }
} else { Write-Host 'ok    2 build smoke (already done)' }
Step '3 bank_check' { uv run --locked python -m workshop.twin.bank.bank_check --bank data/bank/smoke --sample 16 }

if ($script:failed) { Write-Host 'VERIFY 7.1.1: FAIL'; exit 1 }
Write-Host 'VERIFY 7.1.1: PASS'
