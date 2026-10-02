# Verify sub-phase 3.1.2 "Object finder (YOLOE) export". Light by default (no model load):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\3.1.2.ps1
# HEAVY H2 (orchestrator, alone): add -Heavy  (export, parity, shapes, checksums).
param([switch]$Heavy)
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$env:YOLO_AUTOINSTALL = 'False'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok -or $Heavy) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

Check '(1) ruff check + format check' {
  uv run --locked ruff check workshop/forge/yoloe workshop/forge/tests/test_yoloe.py
  if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check workshop/forge/yoloe workshop/forge/tests/test_yoloe.py }
}

Check '(2) pytest test_yoloe.py (numpy NMS/regions, concept score, proposal_pe)' {
  uv run --locked pytest workshop/forge/tests/test_yoloe.py -q
}

if ($Heavy) {
  Check '(3) export (finder + text encoder)' { uv run --locked python -m workshop.forge.yoloe.export }
  Check '(4) parity (AC-3.1-03, AC-3.1-04)' { uv run --locked python -m workshop.forge.yoloe.parity }
  Check '(5) report pass' {
    uv run --locked python -c "import json,sys; r=json.load(open('workshop/forge/yoloe/parity.json')); sys.exit(0 if r['pass'] else 1)"
  }
  Check '(6) shapes fixed, opset 17-20' { uv run --locked python -m workshop.forge.common shapes data/forge/yoloe }
  Check '(7) checksums' {
    uv run --locked python -c "import json,sys; from workshop.forge.common import check_checksums; bad=check_checksums('yoloe'); r=json.load(open('workshop/forge/yoloe/parity.json')); print(bad); sys.exit(0 if (not bad or r['nondeterminism']) else 1)"
  }
}

if ($script:failed) { Write-Host 'VERIFY 3.1.2: FAIL'; exit 1 }
Write-Host 'VERIFY 3.1.2: PASS'
exit 0
