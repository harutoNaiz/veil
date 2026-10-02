# Verify sub-phase 2.2.2 "Burst scheduler". Ends with VERIFY 2.2.2: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false
$files = @('workshop/twin/scheduler.py', 'workshop/twin/tests/test_scheduler.py')
uv run --locked ruff check @files
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run --locked ruff format --check @files
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run pytest workshop/twin/tests/test_scheduler.py -q
if ($LASTEXITCODE -ne 0) { $failed = $true }
if ($failed) { Write-Host 'VERIFY 2.2.2: FAIL'; exit 1 }
Write-Host 'VERIFY 2.2.2: PASS'
