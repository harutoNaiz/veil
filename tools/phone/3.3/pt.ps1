param([switch]$Record, [switch]$DryRun)
. "$PSScriptRoot\common.ps1"
Initialize-Phone -DryRun:$DryRun
$d = @(); if ($DryRun) { $d = @('-DryRun') }
& "$PSScriptRoot\install.ps1" @d
$rec = $null
if ($Record -and -not $DryRun) { $rec = Start-Process scrcpy -ArgumentList "--record=$script:Evidence\pt.mp4" -PassThru }
Invoke-Adb @('shell', 'am', 'start', '-W', '-n', "$script:Pkg/.MainActivity", '--es', 'mode', 'pt')
if (-not $DryRun) { Read-Host 'PT mode shown on the phone; press Enter when done' | Out-Null }
& "$PSScriptRoot\soak.ps1" @d
& "$PSScriptRoot\restart.ps1" @d
if ($rec) { Stop-Process -Id $rec.Id -ErrorAction SilentlyContinue }
if ($DryRun) { return }
Get-Out 'fp.csv'
Set-Location $script:Repo
$ev = $script:Evidence
$ref = 'data\ch3\phone\laptop-fp.csv'
& "$PSScriptRoot\..\..\gradle-locked.ps1" :soak:soakCheck "-Pin=$ev\soak.csv"
& "$PSScriptRoot\..\..\gradle-locked.ps1" :soak:timingReport "-Pin=$ev\timing.csv"
& "$PSScriptRoot\..\..\gradle-locked.ps1" :soak:fpParity "-Pin=$ev\fp.csv" "-Pref=$(Resolve-Path $ref)"
