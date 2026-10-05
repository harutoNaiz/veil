# Proof test "Scroll ruler" (phone only). Writes data/signals/pt-4.2/report.md. Exit 2 = no device.
param([switch]$DryRun)
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$outDir = 'data/signals/pt-4.2'
$name = 'pt42'
$lines = New-Object System.Collections.Generic.List[string]

function Run([string]$desc, [scriptblock]$body, [string]$text) {
  if ($DryRun) { Write-Host "DRYRUN $desc :: $text"; return }
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $desc)
  $lines.Add("### $desc ($(if ($ok) { 'ok' } else { 'FAIL' }))")
  $lines.Add('```'); $out | Select-Object -Last 40 | ForEach-Object { $lines.Add($_) }; $lines.Add('```')
}

if (-not $DryRun) {
  $dev = @(adb devices 2>$null | Select-Object -Skip 1 | Where-Object { $_ -match '\tdevice$' })
  if ($dev.Count -eq 0) { Write-Host 'NO DEVICE'; exit 2 }
  New-Item -ItemType Directory -Force $outDir | Out-Null
}
$bc = 'adb shell am broadcast -a com.veil.guard.LOG -n com.veil.guard/.signals.LogControlReceiver --es cmd'
Run 'install guard' { adb install -r guard\app\build\outputs\apk\debug\app-debug.apk } 'adb install -r app-debug.apk'
Run 'start log' { adb shell am broadcast -a com.veil.guard.LOG -n com.veil.guard/.signals.LogControlReceiver --es cmd start --es name $name } "$bc start --es name $name"
Run 'clear logcat' { adb logcat -c } 'adb logcat -c'

$rng = New-Object System.Random 42
for ($i = 0; $i -lt 100; $i++) {
  if ($i % 5 -eq 4) { $dur = 40; $dy = 1200 } else { $dur = $rng.Next(120, 601); $dy = $rng.Next(300, 900) }
  $y1 = 1700; $y2 = $y1 - $dy
  if ($i % 2) { $y1 = 600; $y2 = $y1 + $dy }
  $cmd = "adb shell input swipe 540 $y1 540 $y2 $dur"
  if ($DryRun) { if ($i -lt 5 -or $i -ge 98) { Write-Host "DRYRUN swipe $i :: $cmd" } elseif ($i -eq 5) { Write-Host 'DRYRUN ...' } }
  else { adb shell input swipe 540 $y1 540 $y2 $dur; Start-Sleep -Milliseconds 400 }
}

Run 'stop log' { adb shell am broadcast -a com.veil.guard.LOG -n com.veil.guard/.signals.LogControlReceiver --es cmd stop --es name $name } "$bc stop --es name $name"
Run 'pull log' { uv run --locked python -m workshop.signals.pull_log --name $name --out $outDir } "python -m workshop.signals.pull_log --name $name --out $outDir"
Run 'scroll ruler' { uv run --locked python -m workshop.signals.scroll_ruler --guard "$outDir/$name.events.jsonl" --truth "$outDir/$name.truth.jsonl" } 'python -m workshop.signals.scroll_ruler --guard ... --truth ...'
Run 'snap cost' { adb logcat -d | Select-String VEIL_SNAP | ForEach-Object { $_.Line } | Set-Content "$outDir/snap.txt" -Encoding utf8; uv run --locked python -m workshop.signals.snap_cost --file "$outDir/snap.txt" } 'python -m workshop.signals.snap_cost --file snap.txt'
Run 'frame stats' { uv run --locked python -m workshop.signals.frame_stats --package com.instagram.android --scrolls 30 } 'python -m workshop.signals.frame_stats'
Run 'perfetto' { adb shell perfetto -o /data/misc/perfetto-traces/pt42.pftrace -t 20s gfx view am; adb pull /data/misc/perfetto-traces/pt42.pftrace "$outDir/pt42.pftrace" } 'adb shell perfetto -t 20s gfx view am'

if ($DryRun) { Write-Host 'DRYRUN done'; exit 0 }
$verdict = if ($lines -match 'FAIL') { 'FAIL' } else { 'PASS (machine part; AC-4.2-02..06 per tool output above; human part pending)' }
@("# Scroll ruler proof test (pt-4.2)", "Date: $(Get-Date -Format s)", "Verdict: $verdict", '') + $lines |
  Set-Content "$outDir/report.md" -Encoding utf8
Write-Host "report: $outDir/report.md"
exit $(if ($verdict -eq 'FAIL') { 1 } else { 0 })
