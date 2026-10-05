# Verify sub-phase 4.2.1 "Accessibility service and event logger". Ends with VERIFY 4.2.1: PASS.
param([switch]$Phone)
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

$main = 'guard/app/src/main/java/com/veil/guard/signals'
$test = 'guard/app/src/test/java/com/veil/guard/signals'
$kt = @('Contracts', 'GuardAccessibilityService', 'EventMapper', 'UiEventJson', 'EventLogger', 'ForegroundTracker',
  'A11yScreenshotSource', 'A11yNode', 'LogControlReceiver') | ForEach-Object { "$main/$_.kt" }
$kt += @('EventMapperTest', 'UiEventJsonTest', 'ForegroundTrackerTest') | ForEach-Object { "$test/$_.kt" }
$py = @('workshop/signals/pull_log.py', 'workshop/signals/tests/test_pull_log.py')

Check '(1) gradle build + 3 tests' {
  & "$repo\guard\gradlew.bat" -p guard --no-daemon :app:assembleDebug :app:testDebugUnitTest `
    --tests 'com.veil.guard.signals.EventMapperTest' --tests 'com.veil.guard.signals.UiEventJsonTest' `
    --tests 'com.veil.guard.signals.ForegroundTrackerTest'
}
Check '(2) 1,000 events validate' {
  uv run --locked python -m workshop.contracts.validate guard\app\build\tmp\uievents-1000.jsonl --type UiEvent --jsonl
}
Check '(3) no tree walks in callbacks' {
  $hits = Select-String -Path "$main/GuardAccessibilityService.kt", "$main/EventMapper.kt" -Pattern 'getChild|rootInActiveWindow|findAccessibilityNodeInfos|getWindows|\.windows\b'
  $global:LASTEXITCODE = [int]($null -ne $hits)
}
Check '(4) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
Check '(5) ruff' { uv run --locked ruff check @py }
Check '(6) pytest' { uv run --locked pytest workshop/signals/tests/test_pull_log.py -q }

if ($Phone) {
  Check '(P) install, log, scroll, pull, validate' {
    adb install -r guard\app\build\outputs\apk\debug\app-debug.apk
    adb shell am broadcast -a com.veil.guard.LOG -n com.veil.guard/.signals.LogControlReceiver --es cmd start --es name v421
    adb shell input swipe 500 1600 500 600 300
    Start-Sleep -Seconds 2
    adb shell am broadcast -a com.veil.guard.LOG -n com.veil.guard/.signals.LogControlReceiver --es cmd stop --es name v421
    uv run --locked python -m workshop.signals.pull_log --name v421 --out data/signals
    uv run --locked python -m workshop.contracts.validate data\signals\v421.events.jsonl --type UiEvent --jsonl
  }
}

if ($script:failed) { Write-Host 'VERIFY 4.2.1: FAIL'; exit 1 }
Write-Host 'VERIFY 4.2.1: PASS'
