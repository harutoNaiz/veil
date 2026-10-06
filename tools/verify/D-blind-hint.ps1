# Verify D-blind-hint.
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
Check '(1) ktlint' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative `
    "guard/app/src/main/java/com/veil/guard/overlay/blind/**/*.kt" `
    "guard/app/src/test/java/com/veil/guard/overlay/blind/**/*.kt"
}
Check '(2) unit tests' {
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\tools\gradle-locked.ps1" :app:testDebugUnitTest --tests "com.veil.guard.overlay.blind.*"
}
Check '(3) compile' {
  & powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\tools\gradle-locked.ps1" :app:compileDebugKotlin
}
if ($script:failed) { Write-Host 'VERIFY D-blind-hint: FAIL'; exit 1 }
Write-Host 'VERIFY D-blind-hint: PASS'
