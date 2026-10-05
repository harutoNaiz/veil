# Verify sub-phase 7.0.1 "Runtime, lifecycle, commands, stage log".
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

$c = 'guard/conductor/src'
$kt = @(
  "$c/main/kotlin/com/veil/conductor/text/GemmaBpe.kt", "$c/main/kotlin/com/veil/conductor/text/ToxPrep.kt",
  "$c/test/kotlin/com/veil/conductor/text/GemmaBpeTest.kt", "$c/test/kotlin/com/veil/conductor/text/ToxPrepTest.kt",
  'guard/app/src/main/java/com/veil/guard/wire/ml/OrtToxicity.kt'
)
function Gradle([string]$a) {
  $log = Join-Path $env:TEMP 'veil-7.0.1-gradle.txt'
  cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\..\gradle-locked.ps1`" $a > `"$log`" 2>&1"
  $code = $LASTEXITCODE
  Get-Content $log | Select-Object -Last 8
  cmd /c "exit $code"
}

Check '(1) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
Check '(2) ruff' { uv run --locked ruff check workshop/forge/toxicity/tokpack.py }
Check '(3) golden' { uv run python -m workshop.forge.toxicity.tokpack --check-golden }
Check '(4) bins exist' {
  $ok = (Test-Path data/forge/toxicity/toxicity-tok.bin) -and (Test-Path data/forge/siglip2/siglip2-tok.bin)
  if ($ok) { cmd /c 'exit 0' } else { cmd /c 'exit 1' }
}
Check '(5) conductor tests' { Gradle ':conductor:test --tests "com.veil.conductor.text.GemmaBpeTest" --tests "com.veil.conductor.text.ToxPrepTest"' }
Check '(6) app compile' { Gradle ':app:compileDebugKotlin' }

if ($script:failed) { Write-Host 'VERIFY 7.0.1: FAIL'; exit 1 }
Write-Host 'VERIFY 7.0.1: PASS'
