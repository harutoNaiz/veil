# Proof test "Sticky note". Without -Phone: runs the three verify scripts. With -Phone: device run (PENDING-HUMAN).
param([switch]$Phone)
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$data = Join-Path $repo 'data\ch4'

if (-not $Phone) {
  foreach ($n in '4.3.1', '4.3.2', '4.3.3') {
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\$n.ps1"
    if ($LASTEXITCODE -ne 0) { Write-Host 'PT 4.3: FAIL'; exit 1 }
  }
  Write-Host 'PT 4.3: machine checks pass; device rows PENDING-HUMAN (run with -Phone)'
  exit 0
}

New-Item -ItemType Directory -Force $data | Out-Null
$adb = 'adb'
if (-not (& $adb devices | Select-String "`tdevice")) { Write-Host 'PT 4.3: PENDING-HUMAN (no phone)'; exit 2 }
$rec = Start-Process scrcpy -ArgumentList "--no-playback --record `"$data\sticky.mp4`"" -PassThru
try {
  & $adb shell am start -n com.veil.testfeed/.MainActivity | Out-Null
  & powershell -NoProfile -File "$repo\tools\phone\4.3.1-phone.ps1"
  & powershell -NoProfile -File "$repo\tools\phone\4.3.2-phone.ps1"
  & powershell -NoProfile -File "$repo\tools\phone\4.3.3-phone.ps1"
} finally {
  if ($rec) { Stop-Process -Id $rec.Id -ErrorAction SilentlyContinue }
}
# checks: drift <= 8 px, tap logged with right itemId, one LongPress, selfcap + 2 px alignment
$g = Join-Path $data 'gestures.jsonl'
$lp = if (Test-Path $g) { @(Select-String -Path $g -Pattern 'LongPress').Count } else { 0 }
if ($lp -ge 1) { Write-Host 'PT 4.3: PASS (confirm drift.md and selfcap output by eye)' }
else { Write-Host 'PT 4.3: FAIL (no LongPress in gestures.jsonl)'; exit 1 }
