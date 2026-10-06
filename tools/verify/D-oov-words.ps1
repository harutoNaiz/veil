# Verify D-oov-words: on-phone SigLIP2 text encoder for out-of-vocabulary words.
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
function Gradle([string]$a) {
  $log = Join-Path $env:TEMP 'veil-D-oov-gradle.txt'
  cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\..\gradle-locked.ps1`" $a > `"$log`" 2>&1"
  $code = $LASTEXITCODE
  Get-Content $log | Select-Object -Last 12
  cmd /c "exit $code"
}
$kt = @(
  'guard/app/src/main/java/com/veil/guard/wire/ml/OovTextEncoder.kt',
  'guard/app/src/test/java/com/veil/guard/wire/ml/Siglip2TokenizerTest.kt',
  'guard/teacher/src/test/kotlin/com/veil/teacher/AutoCalOovTest.kt',
  'guard/app/src/main/java/com/veil/guard/teacher/TeacherDebugActivity.kt'
)
Check '(0) ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative @kt }
Check '(1) kit lists siglip2-text' { if (-not (Select-String -Path tools\phone\kit.ps1 -Pattern 'siglip2-text.onnx' -Quiet)) { cmd /c "exit 1" } else { cmd /c "exit 0" } }
Check '(2) teacher tests + golden token test' { Gradle ':teacher:test :app:testDebugUnitTest --tests *Siglip2TokenizerTest*' }
Check '(3) app compile' { Gradle ':app:compileDebugKotlin' }
if ($script:failed) { Write-Host 'VERIFY D-oov-words: FAIL'; exit 1 }
Write-Host 'VERIFY D-oov-words: PASS'
