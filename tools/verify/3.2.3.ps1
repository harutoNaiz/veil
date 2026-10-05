# Verify sub-phase 3.2.3 "Batch variants, budget, manifests, report". Fixtures only.
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
$own = @('workshop/forge/cloud/budget.py', 'workshop/forge/cloud/manifests.py', 'workshop/forge/cloud/report.py', 'workshop/forge/tests/test_cloud_budget.py')
$tmp = Join-Path $env:TEMP 'veil-3.2.3'
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
Step '1 ruff check' { uv run --locked ruff check @own }
Step '2 ruff format --check' { uv run --locked ruff format --check @own }
Step '3 pytest' { uv run --locked pytest workshop/forge/tests/test_cloud_budget.py -q }
Step '4 budget --fixture' { uv run --locked python -m workshop.forge.cloud.budget --fixture }
Step '5 manifests --fixture' { uv run --locked python -m workshop.forge.cloud.manifests --fixture --out $tmp }
Step '6 manifests --check' { uv run --locked python -m workshop.forge.cloud.manifests --check $tmp }
Step '7 report' { uv run --locked python -m workshop.forge.cloud.report }
Step '8 report has Source' { uv run --locked python -c "import sys; sys.exit(0 if 'Source:' in open('docs/reports/ch3-profile.md', encoding='utf-8').read() else 1)" }
if ($script:failed) { Write-Host 'VERIFY 3.2.3: FAIL'; exit 1 }
Write-Host 'VERIFY 3.2.3: PASS'
