# Verify sub-phase 4.2.3 "Bounded layout snapshot". Ends with VERIFY 4.2.3: PASS.
param([switch]$Phone)
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $good = ($LASTEXITCODE -eq 0)
  if (-not $good) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($good) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $good) { $script:failed = $true }
}

Check '(1) ktlint' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" "guard/app/src/main/java/com/veil/guard/signals/BoundedSnapshotter.kt" "guard/app/src/test/java/com/veil/guard/signals/BoundedSnapshotterTest.kt"
}
Check '(2) ruff' {
  uv run ruff check workshop/signals/snap_cost.py workshop/signals/frame_stats.py workshop/signals/tests/test_snap_cost.py workshop/signals/tests/test_frame_stats.py
  if ($LASTEXITCODE -eq 0) { uv run ruff format --check workshop/signals/snap_cost.py workshop/signals/frame_stats.py workshop/signals/tests/test_snap_cost.py workshop/signals/tests/test_frame_stats.py }
}
Check '(3) pytest' { uv run pytest workshop/signals/tests/test_snap_cost.py workshop/signals/tests/test_frame_stats.py -q }

# wait only for another veil Gradle build (VS Code's Java server and its own Gradle daemon never exit)
while (Get-CimInstance Win32_Process -Filter "Name='java.exe'" | Where-Object { $_.CommandLine -match 'veil-toolchain.*(gradle-wrapper|GradleDaemon)' }) { Start-Sleep -Seconds 10 }
Check '(4) gradle build + BoundedSnapshotterTest' {
  Push-Location guard
  & .\gradlew.bat --no-daemon :app:assembleDebug :app:testDebugUnitTest --tests "com.veil.guard.signals.BoundedSnapshotterTest"
  $ec = $LASTEXITCODE
  Pop-Location
  cmd /c exit $ec
}
if ($Phone) {
  Check '(P1) snap_cost' { uv run python -m workshop.signals.snap_cost }
  Check '(P2) frame_stats' { uv run python -m workshop.signals.frame_stats --package com.instagram.android }
}
if ($script:failed) { Write-Host 'VERIFY 4.2.3: FAIL'; exit 1 }
Write-Host 'VERIFY 4.2.3: PASS'
