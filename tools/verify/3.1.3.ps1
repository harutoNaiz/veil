# Verify sub-phase 3.1.3 "Layer 1 (NudeNet) and toxicity export".
#   tools\verify\3.1.3.ps1            light (ruff + pytest)
#   tools\verify\3.1.3.ps1 -Fetch     H0: network only (NudeNet weights, toxicity model + sample)
#   tools\verify\3.1.3.ps1 -Heavy     H3: export, parity, shapes, checksums  [-L1Set <dir> for HC-3.1-c]
param([switch]$Heavy, [switch]$Fetch, [string]$L1Set = '')
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

if ($Fetch) {
  $env:HF_HUB_DISABLE_XET = '1'
  Check 'fetch NudeNet weights' { uv run python -m workshop.forge.nudenet.fetch }
  Check 'fetch toxicity model + sample' { uv run python -m workshop.forge.toxicity.fetch }
  if ($script:failed) { Write-Host 'FETCH 3.1.3: FAIL'; exit 1 }
  Write-Host 'FETCH 3.1.3: PASS'; exit 0
}

if ($L1Set) {
  Check "L1 positive-class parity on $L1Set (report only)" { uv run python -m workshop.forge.nudenet.parity --l1set $L1Set }
  if ($script:failed) { Write-Host 'L1SET 3.1.3: FAIL'; exit 1 }
  Write-Host 'L1SET 3.1.3: PASS'; exit 0
}

Check '(1) ruff check' {
  uv run --locked ruff check workshop/forge/nudenet workshop/forge/toxicity workshop/forge/tests/test_nudenet.py workshop/forge/tests/test_toxicity.py
}
Check '(2) pytest: decode, agreement, AUC, pad/truncate' {
  uv run --locked pytest workshop/forge/tests/test_nudenet.py workshop/forge/tests/test_toxicity.py -q
}

if ($Heavy) {
  $env:HF_HUB_OFFLINE = '1'
  Check '(3) export NudeNet' { uv run python -m workshop.forge.nudenet.export }
  Check '(4) export toxicity' { uv run python -m workshop.forge.toxicity.export }
  Check '(5) NudeNet parity (harmless images)' { uv run python -m workshop.forge.nudenet.parity }
  Check '(6) toxicity parity' { uv run python -m workshop.forge.toxicity.parity }
  Check '(7) parity.json pass' {
    uv run python -c "import json,sys; sys.exit(0 if all(json.load(open(f'workshop/forge/{m}/parity.json'))['pass'] for m in ('nudenet','toxicity')) else 1)"
  }
  Check '(8) shapes' {
    $a = uv run python -m workshop.forge.common shapes data/forge/nudenet; $c1 = $LASTEXITCODE
    $b = uv run python -m workshop.forge.common shapes data/forge/toxicity; $c2 = $LASTEXITCODE
    $global:LASTEXITCODE = [int]($c1 -ne 0 -or $c2 -ne 0)
  }
  Check '(9) checksums re-check' {
    uv run python -c "import sys; from workshop.forge.common import check_checksums as c; b=c('nudenet')+c('toxicity'); print(b); sys.exit(1 if b else 0)"
  }
}

if ($script:failed) { Write-Host 'VERIFY 3.1.3: FAIL'; exit 1 }
Write-Host 'VERIFY 3.1.3: PASS'
