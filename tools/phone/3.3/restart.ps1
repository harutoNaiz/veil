param([switch]$DryRun)
. "$PSScriptRoot\common.ps1"
Initialize-Phone -DryRun:$DryRun
Invoke-Adb @('shell', 'am', 'force-stop', $script:Pkg)
Invoke-Adb @('logcat', '-c')
Invoke-Adb @('shell', 'am', 'start', '-W', '-n', "$script:Pkg/.MainActivity", '--es', 'mode', 'ready')
if ($script:Dry) { Invoke-Adb @('logcat', '-d', '-s', 'VEIL'); return }
Start-Sleep -Seconds 20
$out = & $env:ADB logcat -d -s VEIL | Select-String 'VEIL_READY'
$out | Tee-Object (Join-Path $script:Evidence 'restart.txt')
if (-not $out) { Write-Host 'restart: no VEIL_READY'; exit 1 }
