# Phone replay for 7.2.3 (needs the iQOO). Pushes the bench replay mp4, pulls the tape-out.
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\phone\7.2.3-phone.ps1 [-Bench data\bench\v1]
param([string]$Bench = 'data\bench\v1')
$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$env:VEIL_ENV_QUIET = '1'
. (Join-Path $repo 'tools\env.ps1')
$devs = @(adb devices 2>$null | Select-Object -Skip 1 | Where-Object { $_ -match '\tdevice$' })
if ($devs.Count -lt 1) { Write-Host 'NO DEVICE'; exit 2 }
$remote = '/sdcard/Android/media/com.veil.guard/replay/'
adb shell mkdir -p $remote
adb push "$Bench\replay\bench-phone.mp4" $remote
adb push "$Bench\replay\bench-phone.session.json" $remote
adb push "$Bench\replay\bench-phone.events.jsonl" $remote
# The Guard replay entry point is not wired yet; when it is, trigger it here and pull the tape-out.
adb pull "${remote}bench-phone.tape-out.jsonl" "$Bench\replay\phone.tape-out.jsonl"
if ($LASTEXITCODE -ne 0) { Write-Host 'PHONE PENDING-HUMAN: no phone tape-out produced'; exit 0 }
uv run --locked python -m workshop.twin.bench.compare --bench $Bench --tape-out "$Bench\replay\phone.tape-out.jsonl" --ccs "$Bench\ccs.json"
exit $LASTEXITCODE
