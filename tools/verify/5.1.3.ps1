# Verify sub-phase 5.1.3 "Teacher and encrypted store".
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
$gradle = Join-Path $repo 'guard\gradlew.bat'
Check '(0) ruff teacher_ref' { uv run --locked ruff check workshop/brain_ref/teacher_ref.py }
Push-Location (Join-Path $repo 'guard')
Check '(1) :teacher:test' { & $gradle --no-daemon '-Pveil.brainOnly=true' :teacher:test }
if (Test-Path (Join-Path $repo 'data\forge\siglip2\siglip2-text.onnx')) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  Check '(2) :teacher:teacherParity' { & $gradle --no-daemon '-Pveil.brainOnly=true' :teacher:teacherParity }
  Write-Host ('parity {0:n0}s' -f $sw.Elapsed.TotalSeconds)
} else { Write-Host 'DEFERRED  (2) teacherParity: siglip2-text.onnx missing' }
Check '(3) app assembleDebug + androidTest' { & $gradle --no-daemon :app:assembleDebug :app:assembleDebugAndroidTest }
Pop-Location
Check '(4) ktlint teacher+app' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" "guard/teacher/src/**/*.kt" "guard/app/src/**/*.kt"
}
if ($script:failed) { Write-Host 'VERIFY 5.1.3: FAIL'; exit 1 }
Write-Host 'VERIFY 5.1.3: PASS'
