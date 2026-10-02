# Verify sub-phase 2.2.3 "Gatekeeper pipeline, look budget, tuning, timeline".
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
$py = 'workshop/twin/gatekeeper.py', 'workshop/twin/budget.py', 'workshop/twin/timeline.py', 'workshop/twin/tests/test_gatekeeper.py', 'workshop/twin/tests/gk_stubs.py'

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $good = ($LASTEXITCODE -eq 0)
  if (-not $good -or $name -like '*budget*') { $out | Select-Object -Last 12 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($good) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $good) { $script:failed = $true }
}

Check '(1) ruff check + format check' {
  uv run --locked ruff check @py
  if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check @py }
}
Check '(2) pytest test_gatekeeper' { uv run pytest workshop/twin/tests/test_gatekeeper.py -q }
Check '(3) budget tune writes params, chart, report' {
  uv run python -m workshop.twin.budget tune
  if ($LASTEXITCODE -ne 0) { return }
  if (-not (Test-Path docs/reports/img/ch2-look-budget.png)) { cmd /c exit 1; return }
  if (-not (Select-String -Path docs/reports/ch2-motion.md -Pattern '## Look budget \(Phase 2.2\)' -Quiet)) { cmd /c exit 1 }
}
Check '(4) budget eval: AC-02 PASS, AC-06 PASS, AC-05 PASS or WAIVER' {
  $o = @(uv run python -m workshop.twin.budget eval)
  $o | ForEach-Object { Write-Host "    $_" }
  $t = $o -join "`n"
  if ($t -notmatch 'AC-2.2-02: PASS' -or $t -notmatch 'AC-2.2-06: PASS' -or $t -notmatch 'AC-2.2-05: (PASS|WAIVER-PROPOSED)') { cmd /c exit 1 } else { cmd /c exit 0 }
}
if ($script:failed) { Write-Host 'VERIFY 2.2.3: FAIL'; exit 1 }
Write-Host 'VERIFY 2.2.3: PASS'
