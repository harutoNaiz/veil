# Verify D-console-bridge: Pigeon regen, Flutter checks + APK, Guard bridge tests, assembleDebug, ktlint.
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
$we = "$repo\tools\with-env.ps1"
$gen = 'console/android/app/src/main/kotlin/com/veil/console/bridge/GuardApi.g.kt'
function Gradle([string]$a) {
  $log = Join-Path $env:TEMP 'veil-dcb-gradle.txt'
  cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\..\gradle-locked.ps1`" $a > `"$log`" 2>&1"
  $code = $LASTEXITCODE
  Get-Content $log | Select-Object -Last 8
  cmd /c "exit $code"
}

Check '(1) pigeon regenerates cleanly (no change, no Kotlin keyword fields)' {
  $before = (Get-FileHash $gen).Hash
  powershell -NoProfile -ExecutionPolicy Bypass -File $we --cd console dart run pigeon --input pigeons/guard_api.dart
  if ($LASTEXITCODE -ne 0) { cmd /c 'exit 1'; return }
  $same = ((Get-FileHash $gen).Hash -eq $before) -and -not (Select-String -Path $gen -Pattern '\bval package\b')
  if ($same) { cmd /c 'exit 0' } else { cmd /c 'exit 1' }
}
Check '(2) flutter analyze' { powershell -NoProfile -ExecutionPolicy Bypass -File $we --cd console flutter analyze --no-fatal-warnings }
Check '(3) flutter test' { powershell -NoProfile -ExecutionPolicy Bypass -File $we --cd console flutter test }
Check '(4) flutter build apk --debug (under Global\veil-gradle)' {
  $mutex = New-Object System.Threading.Mutex($false, 'Global\veil-gradle'); $held = $false
  try {
    try { $held = $mutex.WaitOne([TimeSpan]::FromMinutes(45)) } catch [System.Threading.AbandonedMutexException] { $held = $true }
    powershell -NoProfile -ExecutionPolicy Bypass -File $we --cd console flutter build apk --debug
  } finally { if ($held) { $mutex.ReleaseMutex() }; $mutex.Dispose() }
}
Check '(5) Guard bridge unit tests' { Gradle ':app:testDebugUnitTest --tests com.veil.guard.bridge.*' }
Check '(6) :app:assembleDebug' { Gradle ':app:assembleDebug' }
$b = 'guard/app/src/main/java/com/veil/guard/bridge'
Check '(7) ktlint' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative "$b/*.kt" 'guard/app/src/test/java/com/veil/guard/bridge/*.kt'
}
if ($script:failed) { Write-Host 'VERIFY D-console-bridge: FAIL'; exit 1 }
Write-Host 'VERIFY D-console-bridge: PASS'
