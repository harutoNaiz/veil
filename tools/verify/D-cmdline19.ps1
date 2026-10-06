$ErrorActionPreference = 'Continue'
$tools = Split-Path $PSScriptRoot -Parent
$ok = $true
function Chk($n, $c) { if ($c) { Write-Host "  ok   $n" } else { Write-Host "  FAIL $n"; $script:ok = $false } }
$a = (Get-Content -Raw (Join-Path $tools 'toolchain.json') | ConvertFrom-Json).archives | Where-Object name -eq 'android-cmdline-tools'
Chk 'pin version 19.0' ($a.version -eq '19.0')
Chk 'pin url' ($a.url -eq 'https://dl.google.com/android/repository/commandlinetools-win-13114758_latest.zip')
Chk 'pin sha1' ($a.sha1 -eq '54a582f3bf73e04253602f2d1c80bd5868aac115')
$errs = $null
[void][System.Management.Automation.Language.Parser]::ParseFile((Join-Path $tools 'bootstrap.ps1'), [ref]$null, [ref]$errs)
Chk 'bootstrap.ps1 parses' (@($errs).Count -eq 0)
$env:JAVA_HOME = 'D:\veil-toolchain\jdk17'
$out = (cmd /c "`"D:\veil-toolchain\_trial-cmdline19\cmdline-tools\bin\sdkmanager.bat`" --sdk_root=D:\veil-toolchain\_trial-cmdline19 --version < NUL 2>&1") -join "`n"
Chk "sdkmanager --version = 19.0 ($($out.Trim()))" ($out.Trim() -eq '19.0')
if ($ok) { 'VERIFY D-cmdline19: PASS' } else { 'VERIFY D-cmdline19: FAIL' }
