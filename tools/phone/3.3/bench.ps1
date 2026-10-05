param([ValidateSet('ort-qnn', 'litert-npu')][string]$Runtime = 'ort-qnn', [string]$Model = 'siglip2-image-b1', [int]$N = 100, [switch]$DryRun)
. "$PSScriptRoot\common.ps1"
Initialize-Phone -DryRun:$DryRun
Invoke-Instrument 'com.veil.smoketest.BenchTest' @{ runtime = $Runtime; model = $Model; n = $N }
Get-Out 'timing.csv'
