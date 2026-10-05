# Verify sub-phase 5.2-W.2 "Frames in, real models, concepts".
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
$kt = @("$w/FrameAdapter.kt") + @('ImagePrep', 'ModelStore', 'OrtDescriber', 'OrtNsfwDetector', 'ConceptPack', 'LiveLanes' | ForEach-Object { "$w/ml/$_.kt" }) +
  @('ImagePrepTest', 'ConceptPackTest' | ForEach-Object { "guard/app/src/test/java/com/veil/guard/wire/ml/$_.kt" })
Check '(1) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
function Gradle([string]$a) {
  $log = Join-Path $env:TEMP 'veil-5.2-W.2-gradle.txt'
  cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\..\gradle-locked.ps1`" $a > `"$log`" 2>&1"
  $code = $LASTEXITCODE
  Get-Content $log | Select-Object -Last 8
  cmd /c "exit $code"
}
Check '(2) unit tests' { Gradle ':app:testDebugUnitTest --tests "com.veil.guard.wire.ml.*"' }
Check '(3) compile' { Gradle ':app:compileDebugKotlin' }
foreach ($p in 'Layer1Lane(', 'RegionLane(', 'TextLane(') {
  Check "(4) LiveLanes has $p" { if (Select-String -Path "$w/ml/LiveLanes.kt" -SimpleMatch $p -Quiet) { cmd /c 'exit 0' } else { cmd /c 'exit 1' } }
}
if ($script:failed) { Write-Host 'VERIFY 5.2-W.2: FAIL'; exit 1 } else { Write-Host 'VERIFY 5.2-W.2: PASS' }
