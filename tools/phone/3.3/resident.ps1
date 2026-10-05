param([switch]$DryRun)
. "$PSScriptRoot\common.ps1"
Initialize-Phone -DryRun:$DryRun
Invoke-Instrument 'com.veil.smoketest.ResidentTest'
Get-Out 'timing.csv'
if ($script:Dry) { Invoke-Adb @('shell', 'dumpsys', 'meminfo', $script:Pkg) }
else { & $env:ADB shell dumpsys meminfo $script:Pkg | Tee-Object (Join-Path $script:Evidence 'resident-meminfo.txt') | Select-String 'TOTAL PSS' }
