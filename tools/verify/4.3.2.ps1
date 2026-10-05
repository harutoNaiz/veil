# Verify sub-phase 4.3.2 "Glued test box". Phone part: tools\phone\4.3.2-phone.ps1 (PENDING-HUMAN).
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
  'guard/app/src/main/java/com/veil/guard/overlay/glue/GluedBox.kt',
  'guard/app/src/main/java/com/veil/guard/overlay/glue/GlueController.kt',
  'guard/app/src/test/java/com/veil/guard/overlay/glue/GluedBoxTest.kt'
)
$py = @('workshop/overlay/drift.py', 'workshop/overlay/glue_run.py', 'workshop/overlay/tests/test_drift.py')

Check '(1) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
Check '(2) gradle GluedBoxTest' {
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\tools\gradle-locked.ps1" ':app:testDebugUnitTest' '--tests' 'com.veil.guard.overlay.glue.GluedBoxTest'
}
Check '(3) ruff check' { uv run --locked ruff check @py }
Check '(4) ruff format' { uv run --locked ruff format --check @py }
Check '(5) pytest' { uv run --locked pytest workshop/overlay/tests/test_drift.py -q }

if ($Phone) { Write-Host 'PENDING-HUMAN: run tools\phone\4.3.2-phone.ps1' }
if ($script:failed) { Write-Host 'VERIFY 4.3.2: FAIL'; exit 1 }
Write-Host 'VERIFY 4.3.2: PASS'
