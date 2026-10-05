# Verify sub-phase 4.3.1 "Overlay window and renderer". Ends with VERIFY 4.3.1: PASS.
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

$main = 'guard/app/src/main/java/com/veil/guard/overlay'
$test = 'guard/app/src/test/java/com/veil/guard/overlay'
$kt = @('OverlayApi', 'OverlayRenderer', 'CoverView', 'PlanDiff', 'CoverGeometry', 'MaskPlanJson', 'OverlayCmdReceiver',
  'RenderTrace') | ForEach-Object { "$main/$_.kt" }
$kt += @('PlanDiffTest', 'CoverGeometryTest', 'MaskPlanJsonTest') | ForEach-Object { "$test/$_.kt" }
$kt += 'guard/app/src/debug/java/com/veil/guard/overlay/OverlayAccessibilityService.kt'
$py = @('workshop/overlay/__init__.py', 'workshop/overlay/render_stats.py')

Check '(1) ktlint' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @($kt | Where-Object { $_ -notmatch 'OverlayApi' })
}
Check '(2) gradle build + 3 tests' {
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\tools\gradle-locked.ps1" ':app:assembleDebug' ':app:testDebugUnitTest' `
    '--tests' 'com.veil.guard.overlay.PlanDiffTest' '--tests' 'com.veil.guard.overlay.CoverGeometryTest' `
    '--tests' 'com.veil.guard.overlay.MaskPlanJsonTest'
}
Check '(3) debug service + gestures in manifest' {
  $a = Select-String -Path 'guard/app/src/debug/AndroidManifest.xml' -Pattern 'OverlayAccessibilityService'
  $b = Select-String -Path 'guard/app/src/debug/res/xml/overlay_accessibility_service.xml' -Pattern 'canPerformGestures'
  $global:LASTEXITCODE = [int]($null -eq $a -or $null -eq $b)
}
Check '(4) ruff check' { uv run --locked ruff check @py }
Check '(5) ruff format' { uv run --locked ruff format --check @py }

if ($Phone) { Write-Host 'PENDING-HUMAN: run tools\phone\4.3.1-phone.ps1' }
if ($script:failed) { Write-Host 'VERIFY 4.3.1: FAIL'; exit 1 }
Write-Host 'VERIFY 4.3.1: PASS'
