# Phone steps for 4.3.3 (PENDING-HUMAN: needs the iQOO connected, the debug build installed and the overlay service enabled).
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$data = Join-Path $repo 'data\ch4'
New-Item -ItemType Directory -Force $data | Out-Null
$pkg = 'com.veil.guard'
function Cmd($c, $v) { adb shell am broadcast -a com.veil.guard.overlay.CMD --es cmd $c --es value "$v" | Out-Null }

adb shell run-as $pkg rm -rf files/overlay | Out-Null
Cmd selfcap on
# push a plan with one peekable cover (edit the plan file for your screen)
$plan = Join-Path $data 'plan-4.3.3.json'
if (Test-Path $plan) { Cmd plan (Get-Content $plan -Raw) }
adb shell input swipe 700 2000 700 900 300
Start-Sleep 2
Cmd peekprobe
Start-Sleep 5
# long-press on the peekable cover, then a normal tap
adb shell input swipe 720 1400 720 1400 800
Start-Sleep 1
adb shell input tap 720 1400
Start-Sleep 1
foreach ($f in 'own.jsonl', 'gestures.jsonl', 'peek.jsonl') {
  adb exec-out run-as $pkg cat "files/overlay/$f" > (Join-Path $data $f)
}
# frames: pulled by the 4.1 save_frames flow into data\ch4\frames
$frames = Join-Path $data 'frames\frames.jsonl'
if (Test-Path $frames) {
  Push-Location $repo
  uv run --locked python -m workshop.overlay.own_join $frames (Join-Path $data 'own.jsonl') -o (Join-Path $data 'frames_own.jsonl')
  uv run --locked python -m workshop.overlay.selfcap_check (Join-Path $data 'frames_own.jsonl') (Join-Path $data 'frames')
  Pop-Location
} else { Write-Host 'no frames pulled: enable save_frames and re-run' }
Write-Host 'Check data\ch4\gestures.jsonl for one LongPress and the Test Feed log for the tap.'
