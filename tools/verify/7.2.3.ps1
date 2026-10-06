# Verify sub-phase 7.2.3 "Phone-replay set and twin-vs-phone compare" (no model).
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
function Step([string]$name, [scriptblock]$body) {
  & $body | Out-Host
  if ($LASTEXITCODE -eq 0) { Write-Host "ok    $name" }
  else { Write-Host "FAIL  $name (exit $LASTEXITCODE)"; $script:failed = $true }
}
$py = 'workshop/twin/bench/replay_set.py', 'workshop/twin/bench/compare.py', 'workshop/twin/bench/tests/test_bench_replay.py'
Step '0 ruff' { uv run --locked ruff check --line-length 100 @py; if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check @py } }
Step '1 pytest' { uv run --locked pytest workshop/twin/bench/tests/test_bench_replay.py -q }
Step '2 phone script without device' { powershell -NoProfile -ExecutionPolicy Bypass -File tools\phone\7.2.3-phone.ps1; if ($LASTEXITCODE -eq 2) { cmd /c exit 0 } else { cmd /c exit 1 } }
if ($script:failed) { Write-Host 'VERIFY 7.2.3: FAIL'; exit 1 }
Write-Host 'VERIFY 7.2.3: PASS'
