# Verify sub-phase 3.2.1 "Compile and profile" (fixtures only, no model loading).
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\3.2.1.ps1
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

$owned = 'workshop/forge/cloud/hub.py workshop/forge/cloud/profile.py workshop/forge/cloud/placement.py workshop/forge/tests/test_cloud_profile.py'
Step '1 ruff check' { uv run --locked ruff check workshop/forge/cloud/hub.py workshop/forge/cloud/profile.py workshop/forge/cloud/placement.py workshop/forge/tests/test_cloud_profile.py }
Step '2 ruff format --check' { uv run --locked ruff format --check workshop/forge/cloud/hub.py workshop/forge/cloud/profile.py workshop/forge/cloud/placement.py workshop/forge/tests/test_cloud_profile.py }
Step '3 pytest' { uv run --locked pytest workshop/forge/tests/test_cloud_profile.py -q }
Step '4 profile --fixture' { uv run --locked python -m workshop.forge.cloud.profile --fixture }
Step '5 profile.json keys' {
  uv run --locked python -c "import json,sys; d=json.load(open('workshop/forge/cloud/out/profile.json')); ok=d['source']=='fixture' and len(d['models'])>=9 and all({'modelId','precision','batch','compileJob','profileJob','quantizeJob','latencyMs','peakMemMb','layers','npuShare','offChip'}<=set(m) for m in d['models']); sys.exit(0 if ok else 1)"
}

if ($script:failed) { Write-Host 'VERIFY 3.2.1: FAIL'; exit 1 }
Write-Host 'VERIFY 3.2.1: PASS'
