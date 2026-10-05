# Verify sub-phase 4.1.2 "ScreenSource, small frames, pacing". Ends with VERIFY 4.1.2: PASS.
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

Check '(1) ktlint capture/source' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" "guard/app/src/main/java/com/veil/guard/capture/source/**/*.kt" "guard/app/src/test/java/com/veil/guard/capture/source/**/*.kt"
}
Check '(2) unit tests capture.source' {
  Push-Location guard
  & .\gradlew.bat --no-daemon :app:testDebugUnitTest --tests "com.veil.guard.capture.source.*"
  $ec = $LASTEXITCODE
  Pop-Location
  cmd /c exit $ec
}
if ($script:failed) { Write-Host 'VERIFY 4.1.2: FAIL'; exit 1 }
Write-Host 'VERIFY 4.1.2: PASS'
