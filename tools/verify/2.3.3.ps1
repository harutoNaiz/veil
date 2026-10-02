# Verify sub-phase 2.3.3 "Motion evaluation and golden tapes". Ends with VERIFY 2.3.3: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
$py = 'workshop/twin/oracle.py', 'workshop/twin/motion.py', 'workshop/twin/motion_synth.py', 'workshop/twin/goldens.py', 'workshop/twin/tests/motion_stubs.py', 'workshop/twin/tests/test_motion.py', 'workshop/eval/score_motion.py', 'workshop/eval/tests/test_score_motion.py'

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $good = ($LASTEXITCODE -eq 0)
  if (-not $good) { $out | Select-Object -Last 15 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($good) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $good) { $script:failed = $true }
}

Check '(1) ruff check + format check' {
  uv run --locked ruff check @py
  if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check @py }
}
Check '(2) pytest test_motion + test_score_motion' { uv run pytest workshop/twin/tests/test_motion.py workshop/eval/tests/test_score_motion.py -q }
Check '(3) ensure_test_set' { uv run python -c "from workshop.twin.motion_synth import ensure_test_set; ensure_test_set('data/ch2/synth-test')" }
$s3 = 'data/ch2/synth-test/synth-test-3.session.json'
$s4 = 'data/ch2/synth-test/synth-test-4.session.json'
$o = @(uv run python -m workshop.twin.motion eval --sessions $s3 $s4 --out data/ch2/motion-eval --video balanced)
$ec = $LASTEXITCODE
$o | ForEach-Object { Write-Host "    $_" }
Check '(4) motion eval prints AC lines and the gate line' {
  $t = $o -join "`n"
  if ($ec -ne 0 -or $t -notmatch 'AC-2.3-05' -or $t -notmatch 'GATE ch2 \(synthetic\): (PASS|FAIL)') { cmd /c exit 1 } else { cmd /c exit 0 }
}
if (($o -join "`n") -match 'GATE ch2 \(synthetic\): FAIL') {
  Write-Host '    gate FAIL: running the PLAN fallback once (report-only)'
  $fb = @(uv run python -m workshop.twin.motion eval --sessions $s3 $s4 --out data/ch2/motion-eval-fallback --video none --fallback --modes balanced)
  $fb | ForEach-Object { Write-Host "    $_" }
}
Check '(5) torture eval + report section' {
  uv run python -m workshop.twin.motion eval --sessions data/ch2/synth-test/torture-22.session.json --out data/ch2/motion-eval-torture --video none
  if ($LASTEXITCODE -ne 0) { return }
  $fbArgs = @()
  if (Test-Path data/ch2/motion-eval-fallback/scores.json) { $fbArgs = @('--fallback-scores', 'data/ch2/motion-eval-fallback/scores.json') }
  uv run python -m workshop.twin.motion report --scores data/ch2/motion-eval/scores.json --torture data/ch2/motion-eval-torture/scores.json @fbArgs
  if ($LASTEXITCODE -ne 0) { return }
  if (-not (Select-String -Path docs/reports/ch2-motion.md -Pattern '## Steady covers \(Phase 2.3\)' -Quiet)) { cmd /c exit 1; return }
  if (-not (Select-String -Path docs/reports/ch2-motion.md -Pattern 'GATE ch2 \(synthetic' -Quiet)) { cmd /c exit 1; return }
  if (-not (Select-String -Path data/ch2/motion-eval/scores.json -Pattern '"gate"' -Quiet)) { cmd /c exit 1; return }
  cmd /c exit 0
}
Check '(6) goldens check (>= 3 tapes)' { uv run python -m workshop.twin.goldens check contracts/tapes }
if ($script:failed) { Write-Host 'VERIFY 2.3.3: FAIL'; exit 1 }
Write-Host 'VERIFY 2.3.3: PASS'
