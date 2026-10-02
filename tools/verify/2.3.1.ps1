# Verify sub-phase 2.3.1 "Tracker". Ends with VERIFY 2.3.1: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false
$files = @('workshop/twin/tracker.py', 'workshop/twin/tests/test_tracker.py')
uv run --locked ruff check @files
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run --locked ruff format --check @files
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run pytest workshop/twin/tests/test_tracker.py -q
if ($LASTEXITCODE -ne 0) { $failed = $true }
if ($failed) { Write-Host 'VERIFY 2.3.1: FAIL'; exit 1 }
Write-Host 'VERIFY 2.3.1: PASS'
