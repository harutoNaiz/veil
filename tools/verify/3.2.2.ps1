# Verify sub-phase 3.2.2 "Choose precision per model". No model loading, fixtures only.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
function Step([string]$name, [scriptblock]$body) {
  & $body | Out-Host
  if ($LASTEXITCODE -eq 0) { Write-Host "ok    $name" } else { Write-Host "FAIL  $name"; $script:failed = $true }
}
$p = 'workshop/forge/cloud/precision.py','workshop/forge/cloud/score_adapter.py','workshop/forge/tests/test_cloud_precision.py'
Step '1 ruff check' { uv run --locked ruff check @p }
Step '2 ruff format --check' { uv run --locked ruff format --check @p }
Step '3 pytest' { uv run --locked pytest workshop/forge/tests/test_cloud_precision.py -q }
Step '4 precision --fixture' { uv run --locked python -m workshop.forge.cloud.precision --fixture }
Step '5 json keys' { uv run --locked python -c "import json,sys; d=json.load(open('workshop/forge/cloud/out/precision.json')); sys.exit(0 if d['source'] and all({'modelId','float','candidates','chosen','delta'}<=set(m) for m in d['models']) else 1)" }
if ($script:failed) { Write-Host 'VERIFY 3.2.2: FAIL'; exit 1 }
Write-Host 'VERIFY 3.2.2: PASS'
