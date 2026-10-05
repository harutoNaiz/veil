param([int]$Minutes = 10, [int]$Rate = 3, [switch]$DryRun)
. "$PSScriptRoot\common.ps1"
Initialize-Phone -DryRun:$DryRun
$a = @('shell', 'am', 'instrument', '-w', '-e', 'class', 'com.veil.smoketest.SoakTest', '-e', 'minutes', "$Minutes", '-e', 'rate', "$Rate", "$script:Pkg.test/androidx.test.runner.AndroidJUnitRunner")
if ($script:Dry) { Invoke-Adb $a; Invoke-Adb @('shell', 'dumpsys', 'thermalservice'); Invoke-Adb @('shell', 'dumpsys', 'meminfo', $script:Pkg); return }
$job = Start-Job { param($adb, $argv) & $adb @argv } -ArgumentList $env:ADB, (, $a)
$host_log = Join-Path $script:Evidence 'host-samples.txt'
while ($job.State -eq 'Running') {
  "== $(Get-Date -Format o)" | Add-Content $host_log
  & $env:ADB shell dumpsys thermalservice | Select-String 'Thermal Status|Cached HAL' | Add-Content $host_log
  & $env:ADB shell dumpsys meminfo $script:Pkg | Select-String 'TOTAL PSS' | Add-Content $host_log
  Start-Sleep -Seconds 10
}
Receive-Job $job | Out-Host
Get-Out 'soak.csv'
