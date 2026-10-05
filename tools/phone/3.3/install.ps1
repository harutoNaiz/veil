param([switch]$DryRun)
. "$PSScriptRoot\common.ps1"
Initialize-Phone -DryRun:$DryRun
Set-Location $script:Repo
$apk = 'guard\smoketest\build\outputs\apk'
Invoke-Adb @('install', '-r', '-t', "$apk\debug\smoketest-debug.apk")
Invoke-Adb @('install', '-r', '-t', "$apk\androidTest\debug\smoketest-debug-androidTest.apk")
Invoke-Adb @('shell', 'mkdir', '-p', "$script:Media/models", "$script:Media/screens", "$script:Media/out")
$models = @()
Get-ChildItem data\forge -Recurse -Filter *.onnx -ErrorAction SilentlyContinue | ForEach-Object {
  $models += $_
  Invoke-Adb @('push', $_.FullName, "$script:Media/models/")
}
Get-ChildItem data\forge -Recurse -Filter *.json -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match 'manifest' } | ForEach-Object {
  Invoke-Adb @('push', $_.FullName, "$script:Media/models/")
}
$list = Join-Path $env:TEMP 'veil-models.txt'
if (-not $script:Dry) {
  ($models | ForEach-Object { $id = $_.BaseName; "$id|$($_.Name)|$id.manifest.json" }) | Set-Content -Encoding ascii $list
}
Invoke-Adb @('push', $list, "$script:Media/models.txt")
Invoke-Adb @('push', 'data\ch3\phone\screens\.', "$script:Media/screens/")
Invoke-Adb @('push', 'data\ch3\phone\laptop-fp.csv', "$script:Media/laptop-fp.csv")
