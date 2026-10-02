# Verify sub-phase 2.3.2 "Mask planner and memory". Ends with VERIFY 2.3.2: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false
$files = @('workshop/twin/planner.py', 'workshop/twin/cache.py', 'workshop/twin/tests/test_planner.py', 'workshop/twin/tests/test_cache.py')
uv run --locked ruff check @files
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run --locked ruff format --check @files
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run pytest workshop/twin/tests/test_planner.py workshop/twin/tests/test_cache.py -q -s
if ($LASTEXITCODE -ne 0) { $failed = $true }
if ($failed) { Write-Host 'VERIFY 2.3.2: FAIL'; exit 1 }
Write-Host 'VERIFY 2.3.2: PASS'
