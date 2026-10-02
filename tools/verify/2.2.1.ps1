# Verify sub-phase 2.2.1 "Change detector". Ends with VERIFY 2.2.1: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false
uv run --locked ruff check workshop/twin/change.py workshop/twin/tests/test_change.py
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run ruff format --check workshop/twin/change.py workshop/twin/tests/test_change.py
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run pytest workshop/twin/tests/test_change.py -q
if ($LASTEXITCODE -ne 0) { $failed = $true }
if ($failed) { Write-Host 'VERIFY 2.2.1: FAIL'; exit 1 }
Write-Host 'VERIFY 2.2.1: PASS'
