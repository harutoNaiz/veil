# Verify sub-phase 3.3.1 "Runtime smoke test". Ends with VERIFY 3.3.1: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
function Ok([string]$name, [bool]$good) {
  Write-Host ('{0}  {1}' -f $(if ($good) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $good) { $script:failed = $true }
}

$out = @(& powershell -NoProfile -ExecutionPolicy Bypass -File tools\gradle-locked.ps1 :smoketest:assembleDebug :smoketest:assembleDebugAndroidTest '-Pandroid.uniquePackageNames=false' 2>&1 | ForEach-Object { "$_" })
$g = ($LASTEXITCODE -eq 0)
if (-not $g) { $out | Select-Object -Last 30 | ForEach-Object { Write-Host "    $_" } }
Ok '(1) gradle assembleDebug + assembleDebugAndroidTest' $g

$apk = 'guard\smoketest\build\outputs\apk\debug\smoketest-debug.apk'
$t = 'guard\smoketest\build\outputs\apk\androidTest\debug\smoketest-debug-androidTest.apk'
Ok '(2) both APKs exist' ((Test-Path $apk) -and (Test-Path $t))
if (Test-Path $apk) {
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $z = [IO.Compression.ZipFile]::OpenRead((Resolve-Path $apk))
  $names = @($z.Entries | ForEach-Object { $_.FullName })
  $z.Dispose()
  $libs = @($names | Where-Object { $_ -like 'lib/arm64-v8a/*' -and ($_ -match 'libonnxruntime\.so$|libQnnHtp\.so$|libQnnHtp.*Skel\.so$') })
  $libs | ForEach-Object { Write-Host "    $_" }
  Ok '(3) apk has libonnxruntime.so, libQnnHtp.so, >=1 Skel' (($libs -match 'libonnxruntime\.so$').Count -ge 1 -and ($libs -match 'libQnnHtp\.so$').Count -ge 1 -and ($libs -match 'Skel\.so$').Count -ge 1)
}
Ok '(4) manifest has libcdsprpc.so' ((Get-Content guard\smoketest\src\main\AndroidManifest.xml -Raw) -match 'libcdsprpc\.so')
$bad = @(Get-ChildItem guard\smoketest\src -Recurse -Filter *.kt | Select-String -Pattern 'disable_cpu_ep_fallback.{0,12}["'']0["'']')
Ok '(5) disable_cpu_ep_fallback never set to 0 in src' ($bad.Count -eq 0)
$kt = @(Get-ChildItem guard\smoketest\src -Recurse -Filter *.kt | ForEach-Object { $_.FullName })
$kl = @(& "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" @kt 2>&1)
if ($LASTEXITCODE -ne 0) { $kl | Select-Object -First 15 | ForEach-Object { Write-Host "    $_" } }
Ok '(6) ktlint' ($LASTEXITCODE -eq 0)

if ($script:failed) { Write-Host 'VERIFY 3.3.1: FAIL'; exit 1 }
Write-Host 'VERIFY 3.3.1: PASS'
