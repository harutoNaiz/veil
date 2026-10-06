# Phone-day kit: build every APK, collect into data\phone-kit\apks, write MANIFEST.txt, optionally push to a device.
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\phone\kit.ps1 [-Push] [-DryRun]
param([switch]$Push, [switch]$DryRun)
$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$env:VEIL_ENV_QUIET = '1'
. (Join-Path $repo 'tools\env.ps1')
$kit = Join-Path $repo 'data\phone-kit'; $apkDir = Join-Path $kit 'apks'
$gl = 'tools\gradle-locked.ps1'
$models = @(
  'nudenet\nudenet-320n.onnx', 'nudenet\nudenet-640m.onnx',
  'siglip2\siglip2-image-b1.onnx', 'siglip2\siglip2-image-b4.onnx', 'siglip2\siglip2-image-b16.onnx',
  'siglip2\siglip2-tok.bin', 'siglip2\siglip2-text.onnx',
  'toxicity\toxicity-seq128.onnx', 'toxicity\toxicity-tok.bin',
  'yoloe\yoloe-26s-embed-top100.onnx') | ForEach-Object { "data\forge\$_" }
$concept = 'contracts\examples\compiled-concept\valid-01-cats-siglip2.json'
$remote = '/sdcard/Android/media/com.veil.guard/models/'
$remoteC = '/sdcard/Android/media/com.veil.guard/concepts/'

function Do-Step([string]$name, [scriptblock]$body) {
  Write-Host "STEP  $name"
  if ($DryRun) { return 0 }
  & $body | Out-Host
  $c = $LASTEXITCODE
  if ($c -ne 0) { Write-Host "FAIL  $name (exit $c)" }
  return $c
}
function Gradle([string]$name, [string[]]$a) {
  Do-Step $name { powershell -NoProfile -ExecutionPolicy Bypass -File $gl @a }.GetNewClosure() | Out-Null
}

if ($Push -and -not $DryRun) {
  $devs = @(adb devices 2>$null | Select-Object -Skip 1 | Where-Object { $_ -match '\tdevice$' })
  if ($devs.Count -lt 1) { Write-Host 'NO DEVICE'; exit 2 }
}

if (-not $DryRun) { New-Item -ItemType Directory -Force $apkDir | Out-Null }
$mods = (Get-Content guard\settings.gradle.kts -Raw)
$hasFeed = (Test-Path guard\testfeed\build.gradle.kts) -and $mods -match 'testfeed'
$hasAT = Test-Path guard\app\src\androidTest
$tasks = @(':app:assembleDebug')
if ($hasAT) { $tasks += ':app:assembleDebugAndroidTest' }
if ($hasFeed) { $tasks += ':testfeed:assembleDebug' }
$tasks += ':smoketest:assembleDebug', ':smoketest:assembleDebugAndroidTest'
Gradle 'gradle build all Android APKs' $tasks

# Flutter console APK (D-6.1-apk), under the same mutex so it never overlaps a Gradle build.
Write-Host 'STEP  flutter build apk --debug (console, under Global\veil-gradle)'
$flutterOk = $true
if (-not $DryRun) {
  $mutex = New-Object System.Threading.Mutex($false, 'Global\veil-gradle'); $held = $false
  try {
    try { $held = $mutex.WaitOne([TimeSpan]::FromMinutes(45)) } catch [System.Threading.AbandonedMutexException] { $held = $true }
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd console flutter build apk --debug | Out-Host
    if ($LASTEXITCODE -ne 0) { $flutterOk = $false; Write-Host 'WARN  flutter build failed (D-6.1-apk not satisfied)' }
  } finally { if ($held) { $mutex.ReleaseMutex() }; $mutex.Dispose() }
}

Write-Host "STEP  copy APKs to $apkDir"
$src = [ordered]@{
  'guard-debug.apk'           = 'guard\app\build\outputs\apk\debug\app-debug.apk'
  'guard-androidTest.apk'     = 'guard\app\build\outputs\apk\androidTest\debug\app-debug-androidTest.apk'
  'testfeed-debug.apk'        = 'guard\testfeed\build\outputs\apk\debug\testfeed-debug.apk'
  'smoketest-debug.apk'       = 'guard\smoketest\build\outputs\apk\debug\smoketest-debug.apk'
  'smoketest-androidTest.apk' = 'guard\smoketest\build\outputs\apk\androidTest\debug\smoketest-debug-androidTest.apk'
  'console-debug.apk'         = 'console\build\app\outputs\flutter-apk\app-debug.apk'
}
$copied = @()
if (-not $DryRun) {
  foreach ($k in $src.Keys) {
    if (Test-Path $src[$k]) { Copy-Item $src[$k] (Join-Path $apkDir $k) -Force; $copied += $k }
    else { Write-Host "WARN  missing $($src[$k])" }
  }
  Write-Host 'STEP  write MANIFEST.txt'
  $lines = @("Veil phone kit  $(Get-Date -Format s)", '', '[APKs]')
  foreach ($f in Get-ChildItem $apkDir -Filter *.apk) {
    $lines += ('{0}  {1} bytes  sha256={2}' -f $f.Name, $f.Length, (Get-FileHash $f.FullName -Algorithm SHA256).Hash)
  }
  $lines += '', "[models -> $remote]"
  foreach ($m in $models) {
    if (Test-Path $m) { $lines += ('{0}  {1} bytes' -f $m, (Get-Item $m).Length) } else { $lines += "$m  MISSING" }
  }
  $lines += '', "[concept -> $remoteC]"
  $lines += $(if (Test-Path $concept) { '{0}  {1} bytes' -f $concept, (Get-Item $concept).Length } else { "$concept  MISSING" })
  $lines | Set-Content (Join-Path $kit 'MANIFEST.txt') -Encoding utf8
} else {
  Write-Host 'STEP  write MANIFEST.txt'
}

if ($Push) {
  foreach ($k in $src.Keys) {
    Do-Step "adb install -r -t $k" { if (Test-Path "$apkDir\$k") { adb install -r -t "$apkDir\$k" } else { $global:LASTEXITCODE = 0 } }.GetNewClosure() | Out-Null
  }
  Do-Step "adb mkdir models/concepts" { adb shell mkdir -p $remote $remoteC }.GetNewClosure() | Out-Null
  foreach ($m in $models) {
    Do-Step "adb push $m" { if (Test-Path $m) { adb push $m $remote } else { Write-Host "skip missing $m"; $global:LASTEXITCODE = 0 } }.GetNewClosure() | Out-Null
  }
  foreach ($b in @(@('bank.bin', 'bank-v1.bin'), @('vocab.bin', 'vocab-v1.bin'), @('vocab.json', 'vocab-v1.json'))) {
    $bf = "data\bank\v1\$($b[0])"; $bt = "$remote$($b[1])"
    if (Test-Path $bf) { Do-Step "adb push $($b[1])" { adb push $bf $bt }.GetNewClosure() | Out-Null }
  }
  Do-Step "adb push concept" { adb push $concept $remoteC }.GetNewClosure() | Out-Null
}
Write-Host "kit done (flutter ok: $flutterOk)"
exit 0
