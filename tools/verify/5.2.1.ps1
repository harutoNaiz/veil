# Verify sub-phase 5.2.1 "The conductor". Ends with VERIFY 5.2.1: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  $out | Where-Object { $_ -match 'PARITY|SKIP synth' } | ForEach-Object { Write-Host "    $_" }
  if (-not $ok) { $out | Select-Object -Last 30 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}
$g = "$repo\tools\gradle-locked.ps1"
Check '(1) ConductorTest + ReplayParityTest' {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $g '-Pveil.brainOnly=true' :conductor:test --tests 'com.veil.conductor.ConductorTest' --tests 'com.veil.conductor.ReplayParityTest'
}
$x = Join-Path $repo 'guard/conductor/build/test-results/test/TEST-com.veil.conductor.ReplayParityTest.xml'
if (Test-Path $x) { Select-String -Path $x -Pattern 'PARITY|SKIP synth' | ForEach-Object { Write-Host "    $($_.Line.Trim())" } }
Check '(2) app compileDebugKotlin' {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $g :app:compileDebugKotlin
}
$kt = @('Ports', 'Conductor', 'Thumbs', 'Replay') | ForEach-Object { "guard/conductor/src/main/kotlin/com/veil/conductor/$_.kt" }
$kt += @('ConductorTest', 'ReplayParityTest', 'Fakes') | ForEach-Object { "guard/conductor/src/test/kotlin/com/veil/conductor/$_.kt" }
$kt += 'guard/app/src/debug/java/com/veil/guard/replay/ReplayActivity.kt'
Check '(3) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @($kt) }
if ($script:failed) { Write-Host 'VERIFY 5.2.1: FAIL'; exit 1 }
Write-Host 'VERIFY 5.2.1: PASS'
