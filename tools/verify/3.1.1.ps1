# Verify sub-phase 3.1.1 "Describer (SigLIP2) export + PT-3.1 harness".
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\3.1.1.ps1 [-Heavy]
# Light mode never loads real model weights. -Heavy (HEAVY H1, run alone): export, parity, shapes, checksums.
param([switch]$Heavy)
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

Step '1 ruff check' { uv run --locked ruff check workshop/forge/common.py workshop/forge/siglip2 workshop/forge/proof.py workshop/forge/tests }
Step '2 ruff format --check' { uv run --locked ruff format --check workshop/forge/common.py workshop/forge/siglip2 workshop/forge/proof.py workshop/forge/tests/test_common.py workshop/forge/tests/test_siglip2.py workshop/forge/tests/test_proof.py }
Step '3 pytest common/siglip2/proof' { uv run --locked pytest workshop/forge/tests/test_common.py workshop/forge/tests/test_siglip2.py workshop/forge/tests/test_proof.py -q }

if ($Heavy) {
  Step '4 export' { uv run --locked python -m workshop.forge.siglip2.export --out data/forge/siglip2 }
  Step '5 parity' { uv run --locked python -m workshop.forge.siglip2.parity }
  Step '6 parity.json pass' { uv run --locked python -c "import json,sys; sys.exit(0 if json.load(open('workshop/forge/siglip2/parity.json'))['pass'] else 1)" }
  Step '7 shapes' { uv run --locked python -m workshop.forge.common shapes data/forge/siglip2 }
  Step '8 checksums re-check' { uv run --locked python -c "import json,sys; from workshop.forge import common; bad=common.check_checksums('siglip2'); nd=json.load(open('workshop/forge/siglip2/parity.json')).get('nondeterminism',''); print('mismatch:',bad); sys.exit(0 if (not bad or nd) else 1)" }
}

if ($script:failed) { Write-Host 'VERIFY 3.1.1: FAIL'; exit 1 }
Write-Host 'VERIFY 3.1.1: PASS'
