# Verify sub-phase 4.2.2 "Accurate scrolling". -Phone: proof test pt-4.2 is human-run.
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

$kt = @(
  'guard/app/src/main/java/com/veil/guard/signals/ScrollTracker.kt',
  'guard/app/src/main/java/com/veil/guard/signals/FrameShiftEstimator.kt',
  'guard/app/src/test/java/com/veil/guard/signals/ScrollTrackerTest.kt',
  'guard/app/src/test/java/com/veil/guard/signals/FrameShiftEstimatorTest.kt'
)
$py = @('workshop/signals/scroll_ruler.py', 'workshop/signals/tests/test_scroll_ruler.py')

Check '(1) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
# wait only for another veil Gradle build (VS Code's Java server and its own Gradle daemon never exit)
while (Get-CimInstance Win32_Process -Filter "Name='java.exe'" | Where-Object { $_.CommandLine -match 'veil-toolchain.*(gradle-wrapper|GradleDaemon)' }) { Start-Sleep -Seconds 10 }
$gradle = Join-Path $repo 'guard\gradlew.bat'
Push-Location (Join-Path $repo 'guard')
Check '(2) gradle tests' {
  & $gradle --no-daemon ':app:testDebugUnitTest' '--tests' 'com.veil.guard.signals.ScrollTrackerTest' '--tests' 'com.veil.guard.signals.FrameShiftEstimatorTest'
}
Pop-Location
Check '(3) ruff check' { uv run --locked ruff check @py }
Check '(4) ruff format' { uv run --locked ruff format --check @py }
Check '(5) pytest' { uv run --locked pytest workshop/signals/tests/test_scroll_ruler.py -q }

if ($Phone) { Write-Host 'PENDING-HUMAN: phone part runs via tools\verify\pt-4.2.ps1' }
if ($script:failed) { Write-Host 'VERIFY 4.2.2: FAIL'; exit 1 }
Write-Host 'VERIFY 4.2.2: PASS'
