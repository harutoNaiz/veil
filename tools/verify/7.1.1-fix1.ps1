# Verify 7.1.1-fix1 "GPU bank engine".
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
Remove-Item -Recurse -Force data/bank/smoke-gpu -ErrorAction SilentlyContinue
Step '2 gpu smoke build' { uv run --locked --with onnxruntime-directml python -m workshop.twin.bank.build_bank --engine onnx --provider dml --limit 48 --ui 0 --vocab-limit 50 --out data/bank/smoke-gpu }
Step '3 gpu bank_check' { uv run --locked --with onnxruntime-directml python -m workshop.twin.bank.bank_check --engine onnx --provider dml --bank data/bank/smoke-gpu --sample 16 }
Step '4 torch-cpu vs bank (cross-engine)' { uv run --locked python -m workshop.twin.bank.bank_check --engine torch --bank data/bank/smoke-gpu --sample 16 }
if ($script:failed) { Write-Host 'VERIFY 7.1.1-fix1: FAIL'; exit 1 }
Write-Host 'VERIFY 7.1.1-fix1: PASS'
