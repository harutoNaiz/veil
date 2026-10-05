# Verify sub-phase 5.2-W.1 "Runtime, lifecycle, commands, stage log".
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

$w = 'guard/app/src/main/java/com/veil/guard/wire'
$kt = @(
  "$w/WireHub.kt", "$w/GuardCore.kt", "$w/GuardRuntime.kt", "$w/ThreadWorker.kt", "$w/StageTracker.kt", "$w/JsonlDebugLog.kt",
  'guard/app/src/main/java/com/veil/guard/capture/service/CaptureService.kt',
  'guard/app/src/test/java/com/veil/guard/wire/GuardCoreWiringTest.kt',
  'guard/app/src/test/java/com/veil/guard/wire/StageTrackerTest.kt'
)
function Gradle([string]$a) {
  $log = Join-Path $env:TEMP 'veil-5.2-W.1-gradle.txt'
  cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\..\gradle-locked.ps1`" $a > `"$log`" 2>&1"
  $code = $LASTEXITCODE
  Get-Content $log | Select-Object -Last 8
  cmd /c "exit $code"
}

Check '(1) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
Check '(2) params asset == twin' {
  $a = (Get-FileHash guard/app/src/main/assets/params.json -Algorithm SHA256).Hash
  $b = (Get-FileHash workshop/twin/params.json -Algorithm SHA256).Hash
  if ($a -eq $b) { cmd /c 'exit 0' } else { cmd /c 'exit 1' }
}
Check '(3) CaptureService wiring' {
  $s = 'guard/app/src/main/java/com/veil/guard/capture/service/CaptureService.kt'
  $ok = (Select-String -Path $s -SimpleMatch 'GuardRuntime.start') -and (Select-String -Path $s -SimpleMatch 'FrameAdapter.sink') -and (Select-String -Path $s -SimpleMatch '"mode"')
  if ($ok) { cmd /c 'exit 0' } else { cmd /c 'exit 1' }
}
Check '(4) unit tests' { Gradle ':app:testDebugUnitTest --tests com.veil.guard.wire.GuardCoreWiringTest --tests com.veil.guard.wire.StageTrackerTest' }
Check '(5) assembleDebug' { Gradle ':app:assembleDebug' }

if ($script:failed) { Write-Host 'VERIFY 5.2-W.1: FAIL'; exit 1 }
Write-Host 'VERIFY 5.2-W.1: PASS'
