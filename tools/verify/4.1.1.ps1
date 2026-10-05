# Verify sub-phase 4.1.1 "Service, consent, state machine".
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

$owned = @(
  'guard/app/src/main/java/com/veil/guard/capture/CaptureApi.kt',
  'guard/app/src/main/java/com/veil/guard/capture/CaptureLog.kt',
  'guard/app/src/main/java/com/veil/guard/capture/state/CaptureStateMachine.kt',
  'guard/app/src/main/java/com/veil/guard/capture/state/EntireScreenCheck.kt',
  'guard/app/src/main/java/com/veil/guard/capture/service/CaptureService.kt',
  'guard/app/src/main/java/com/veil/guard/capture/service/ConsentActivity.kt',
  'guard/app/src/main/java/com/veil/guard/capture/service/CaptureNotifications.kt',
  'guard/app/src/main/java/com/veil/guard/capture/service/CaptureCommandReceiver.kt',
  'guard/app/src/test/java/com/veil/guard/capture/state/CaptureStateMachineTest.kt',
  'guard/app/src/test/java/com/veil/guard/capture/state/EntireScreenCheckTest.kt'
)

Check '(1) ktlint owned Kotlin' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @owned
}

$gradle = Join-Path $repo 'guard\gradlew.bat'
Push-Location (Join-Path $repo 'guard')
Check '(2) state machine unit tests' {
  & $gradle --no-daemon ':app:testDebugUnitTest' '--tests' 'com.veil.guard.capture.state.*'
}
Check '(3) app assembleDebug' {
  & $gradle --no-daemon ':app:assembleDebug'
}
Pop-Location

Check '(4) manifest has mediaProjection service type + permission' {
  $xml = Get-Content (Join-Path $repo 'guard\app\src\main\AndroidManifest.xml') -Raw
  $ok = ($xml -match 'foregroundServiceType="mediaProjection"') -and
        ($xml -match 'FOREGROUND_SERVICE_MEDIA_PROJECTION')
  $global:LASTEXITCODE = [int](-not $ok)
}

if ($script:failed) { Write-Host 'VERIFY 4.1.1: FAIL'; exit 1 }
Write-Host 'VERIFY 4.1.1: PASS'
