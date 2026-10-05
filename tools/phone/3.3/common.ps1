# Shared helpers for the 3.3 phone scripts. Dot-source: . "$PSScriptRoot\common.ps1"
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\..\env.ps1"
$script:Repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$script:Pkg = 'com.veil.smoketest'
$script:Media = "/sdcard/Android/media/$script:Pkg"
$script:Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$script:Evidence = Join-Path $script:Repo "data\ch3\phone\$script:Stamp"
$script:Dry = $false

function Initialize-Phone([switch]$DryRun) {
  $script:Dry = [bool]$DryRun
  if ($script:Dry) { return }
  $devs = @(& $env:ADB devices | Select-String -Pattern "`tdevice$")
  if ($devs.Count -lt 1) { Write-Host 'NO PHONE'; exit 2 }
  New-Item -ItemType Directory -Force $script:Evidence | Out-Null
}

# Run adb (or print it in dry-run mode).
function Invoke-Adb([string[]]$AdbArgs) {
  if ($script:Dry) { Write-Host ('adb ' + ($AdbArgs -join ' ')); return }
  & $env:ADB @AdbArgs
}

function Invoke-Instrument([string]$Class, [hashtable]$Extra = @{}) {
  $a = @('shell', 'am', 'instrument', '-w', '-e', 'class', $Class)
  foreach ($k in $Extra.Keys) { $a += @('-e', $k, [string]$Extra[$k]) }
  $a += "$script:Pkg.test/androidx.test.runner.AndroidJUnitRunner"
  Invoke-Adb $a
}

function Get-Out([string]$Name) {
  Invoke-Adb @('pull', "$script:Media/out/$Name", $script:Evidence)
}
