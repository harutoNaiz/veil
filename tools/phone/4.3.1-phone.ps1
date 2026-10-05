# Phone steps for 4.3.1 (needs the iQOO connected). Debug build hosts the overlay via OverlayAccessibilityService.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$svc = 'com.veil.guard/com.veil.guard.overlay.OverlayAccessibilityService'
adb install -r guard\app\build\outputs\apk\debug\app-debug.apk
$cur = (adb shell settings get secure enabled_accessibility_services).Trim()
if ($cur -notlike "*$svc*") {
  $new = if ($cur -and $cur -ne 'null') { "${cur}:$svc" } else { $svc }
  adb shell settings put secure enabled_accessibility_services $new
  adb shell settings put secure accessibility_enabled 1
}
$plan = Get-Content -Raw contracts\examples\mask-plan\valid-01-two-covers.json
adb shell am broadcast -a com.veil.guard.overlay.CMD -n com.veil.guard/.overlay.OverlayCmdReceiver --es cmd plan --es value "'$plan'"
foreach ($pkg in 'com.instagram.android', 'com.google.android.youtube', 'com.android.chrome') {
  adb shell monkey -p $pkg -c android.intent.category.LAUNCHER 1
  Start-Sleep -Seconds 3
  adb exec-out screencap -p > "data\ch4\ov-$pkg.png"
  adb shell input tap 700 400   # under a cover: the app below must receive it (check testfeed log)
}
adb exec-out run-as com.veil.guard cat files/overlay/render.jsonl > data\ch4\render.jsonl
uv run --locked python -m workshop.overlay.render_stats data\ch4\render.jsonl
Write-Host 'NEEDS_HUMAN: confirm covers above keyboard and status bar visually; run 5-app tap-through.'
