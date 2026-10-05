# Verify sub-phase 5.2-W.3 "Signals and overlay host".
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
$m = 'guard/app/src/main/java/com/veil/guard'
$kt = @("$m/signals/GuardAccessibilityService.kt", "$m/overlay/OverlayRenderer.kt",
  "$m/wire/EventAdapter.kt", "$m/wire/PlanRecords.kt", "$m/wire/LayoutFeed.kt", "$m/wire/LiveOverlay.kt",
  'guard/app/src/test/java/com/veil/guard/wire/EventAdapterTest.kt',
  'guard/app/src/test/java/com/veil/guard/wire/PlanRecordsTest.kt')
Check '(1) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
Check '(2) gradle tests + compile' {
  $log = Join-Path $env:TEMP 'veil-5.2-W.3-gradle.txt'
  cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\..\gradle-locked.ps1`" :app:testDebugUnitTest --tests com.veil.guard.wire.EventAdapterTest --tests com.veil.guard.wire.PlanRecordsTest :app:compileDebugKotlin > `"$log`" 2>&1"
  $code = $LASTEXITCODE
  Get-Content $log | Select-Object -Last 15
  cmd /c "exit $code"
}
Check '(3) service wiring' {
  $s = Get-Content "$m/signals/GuardAccessibilityService.kt" -Raw
  $ok = $true
  foreach ($p in 'OverlayHostRegistry.host = OverlayRenderer()', 'SelfCapture.install(this)', '.register()', 'CoverTouchLayer(', 'glue?.onEvent(raw)', 'WireHub.events') {
    if (-not $s.Contains($p)) { Write-Host "    missing: $p"; $ok = $false }
  }
  cmd /c "exit $(if ($ok) { 0 } else { 1 })"
}
if ($script:failed) { Write-Host 'VERIFY 5.2-W.3: FAIL'; exit 1 }
Write-Host 'VERIFY 5.2-W.3: PASS'
