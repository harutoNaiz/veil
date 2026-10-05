# Verify sub-phase 7.0.3 "Runtime, lifecycle, commands, stage log".
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

$a = 'guard/app/src/main/java/com/veil/guard'
$kt = @(
  "$a/wire/GuardCore.kt", "$a/wire/GuardRuntime.kt", "$a/wire/ml/LiveLanes.kt", "$a/wire/ml/ModelStore.kt",
  "$a/wire/ml/ConceptWatcher.kt", "$a/teacher/TeacherDebugActivity.kt",
  'guard/app/src/test/java/com/veil/guard/wire/LaneSwapTest.kt'
)
function Gradle([string]$a) {
  $log = Join-Path $env:TEMP 'veil-7.0.3-gradle.txt'
  cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\..\gradle-locked.ps1`" $a > `"$log`" 2>&1"
  $code = $LASTEXITCODE
  Get-Content $log | Select-Object -Last 8
  cmd /c "exit $code"
}

function Has([string]$f, [string]$t) { if (Select-String -Path $f -SimpleMatch $t) { cmd /c 'exit 0' } else { cmd /c 'exit 1' } }

Check '(1) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
Check '(2) unit tests' { Gradle ':app:testDebugUnitTest --tests com.veil.guard.wire.LaneSwapTest --tests com.veil.guard.wire.GuardCoreWiringTest' }
Check '(3) LiveLanes OrtToxicity.open' { Has "$a/wire/ml/LiveLanes.kt" 'OrtToxicity.open(' }
Check '(4) GuardRuntime ConceptWatcher' { Has "$a/wire/GuardRuntime.kt" 'ConceptWatcher(' }
Check '(5) GuardRuntime swapLanes' { Has "$a/wire/GuardRuntime.kt" 'swapLanes()' }
Check '(6) assembleDebug' { Gradle ':app:assembleDebug' }

if ($script:failed) { Write-Host 'VERIFY 7.0.3: FAIL'; exit 1 }
Write-Host 'VERIFY 7.0.3: PASS'
