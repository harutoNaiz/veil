# Verify sub-phase 4.3.3 "Self-capture, own-cover reporting, peek, long-press". Phone part: tools\phone\4.3.3-phone.ps1.
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

$ov = 'guard/app/src/main/java/com/veil/guard/overlay'
$kt = @(
  "$ov/self/OwnOverlayRegistry.kt", "$ov/self/PeekProbe.kt", "$ov/self/SelfCapture.kt",
  "$ov/touch/LongPressDetector.kt", "$ov/touch/TouchReplay.kt", "$ov/touch/CoverTouchLayer.kt",
  'guard/app/src/test/java/com/veil/guard/overlay/OwnOverlayRegistryTest.kt',
  'guard/app/src/test/java/com/veil/guard/overlay/LongPressDetectorTest.kt',
  'guard/app/src/test/java/com/veil/guard/overlay/TouchReplayTest.kt'
)
$py = @('workshop/overlay/own_join.py', 'workshop/overlay/selfcap_check.py', 'workshop/overlay/tests/test_own_join.py')

Check '(1) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
Check '(2) gradle tests' {
  # cmd redirect: the wrapper's Stop preference turns Gradle's stderr warnings into errors otherwise
  $log = Join-Path $env:TEMP 'veil-4.3.3-gradle.txt'
  $a = '--tests com.veil.guard.overlay.OwnOverlayRegistryTest --tests com.veil.guard.overlay.LongPressDetectorTest --tests com.veil.guard.overlay.TouchReplayTest'
  cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\..\gradle-locked.ps1`" :app:testDebugUnitTest $a > `"$log`" 2>&1"
  $code = $LASTEXITCODE
  Get-Content $log | Select-Object -Last 8
  cmd /c "exit $code"
}
Check '(3) ruff check' { uv run --locked ruff check @py }
Check '(4) ruff format' { uv run --locked ruff format --check @py }
Check '(5) pytest' { uv run --locked pytest workshop/overlay/tests/test_own_join.py -q }

if ($Phone) { Write-Host 'PENDING-HUMAN: phone part runs via tools\phone\4.3.3-phone.ps1' }
if ($script:failed) { Write-Host 'VERIFY 4.3.3: FAIL'; exit 1 }
Write-Host 'VERIFY 4.3.3: PASS'
