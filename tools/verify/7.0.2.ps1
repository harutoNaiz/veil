# Verify sub-phase 7.0.2 "Guard crash recovery and Resume Veil".
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

$b = 'guard/app/src/main/java/com/veil/guard/capture'
$t = 'guard/app/src/test/java/com/veil/guard/capture'
$owned = @("$b/service/CaptureService.kt", "$b/service/CaptureNotifications.kt", "$b/service/RecoveryPolicy.kt",
  "$b/state/CaptureStateMachine.kt", "$t/service/RecoveryPolicyTest.kt", "$t/service/GuardRecoveryLoopTest.kt",
  "$t/state/CaptureStateMachineTest.kt")
$locked = Join-Path $repo 'tools\gradle-locked.ps1'

Check '(1) ktlint owned Kotlin' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @owned
}
Check '(2) unit tests' {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $locked ':app:testDebugUnitTest' '--tests' 'com.veil.guard.capture.service.*' '--tests' 'com.veil.guard.capture.state.CaptureStateMachineTest'
}
Check '(3) RECOVERY-GUARD line' {
  $f = Join-Path $repo 'guard\app\build\test-results\testDebugUnitTest\TEST-com.veil.guard.capture.service.GuardRecoveryLoopTest.xml'
  $ok = [bool](Select-String -Path $f -SimpleMatch 'RECOVERY-GUARD crash=5/5 lock=5/5 kill=5/5' -Quiet)
  $global:LASTEXITCODE = [int](-not $ok)
}
Check '(4) service source markers' {
  $f = Join-Path $repo "$b/service/CaptureService.kt"
  $ok = (Select-String -Path $f -SimpleMatch 'FOREGROUND_SERVICE_TYPE_SPECIAL_USE' -Quiet) -and
        (Select-String -Path $f -SimpleMatch 'RecoveryPolicy.onStart' -Quiet)
  $global:LASTEXITCODE = [int](-not $ok)
}
Check '(5) processDebugMainManifest' {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $locked ':app:processDebugMainManifest'
}

if ($script:failed) { Write-Host 'VERIFY 7.0.2: FAIL'; exit 1 }
Write-Host 'VERIFY 7.0.2: PASS'
