# Verify sub-phase 4.1.3 "Backup capture, blind spots, driver routine".
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

Check '(1) ktlint' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative `
    "guard/app/src/main/java/com/veil/guard/capture/backup/**/*.kt" `
    "guard/app/src/main/java/com/veil/guard/capture/blind/**/*.kt" `
    "guard/app/src/test/java/com/veil/guard/capture/backup/**/*.kt" `
    "guard/app/src/test/java/com/veil/guard/capture/blind/**/*.kt"
}
Check '(2) ruff' {
  uv run --locked ruff check workshop/bench/capture_routine.py workshop/bench/capture_logs.py workshop/bench/tests/test_capture_logs.py
}
Check '(3) pytest capture_logs' { uv run --locked pytest workshop/bench/tests/test_capture_logs.py -q }
Check '(4) capture_routine --dry-run' {
  $o = uv run python -m workshop.bench.capture_routine --dry-run
  $o | ForEach-Object { Write-Host "    $_" }
  $global:LASTEXITCODE = [int](-not ($o -match 'Netflix'))
}
Check '(5) JVM tests backup + blind' {
  & "$repo\guard\gradlew.bat" -p guard --no-daemon :app:testDebugUnitTest --tests "com.veil.guard.capture.backup.*" --tests "com.veil.guard.capture.blind.*"
}

if ($script:failed) { Write-Host 'VERIFY 4.1.3: FAIL'; exit 1 }
Write-Host 'VERIFY 4.1.3: PASS'
