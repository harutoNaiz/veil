# Proof test 5.3 "A day in 30 minutes" (PHONE, ~4 h; run in background). Uses Gradle for tapeTest.
param([string]$Brightness = '128')
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$log = Join-Path $repo 'data\ch5\perf\pt.log'
$ev = Join-Path $repo 'progress\ch5-guard\phase-5.3-real-world-performance\evidence'
$runs = Join-Path $repo 'data\ch5\perf\runs.json'
New-Item -ItemType Directory -Force (Split-Path $log), $ev | Out-Null
Start-Transcript -Path $log -Append | Out-Null
$script:failed = $false
function Step([string]$name, [scriptblock]$body) {
  & $body
  if ($LASTEXITCODE -ne 0) { Write-Host "FAIL $name"; $script:failed = $true } else { Write-Host "ok   $name" }
}
function Done([string]$s) { Write-Host "PT 5.3: $s"; Stop-Transcript | Out-Null; exit $(if ($s -eq 'FAIL') { 1 } else { 0 }) }

$dev = @(adb devices | Select-String "`tdevice$")
if ($dev.Count -ne 1) { Write-Host 'NO DEVICE (need exactly one)'; Done 'PENDING' }
Step 'brain tapeTest' { Push-Location guard; & .\gradlew.bat --no-daemon '-Pveil.brainOnly=true' :brain:tapeTest; $c = $LASTEXITCODE; Pop-Location; cmd /c exit $c }
adb shell settings put system screen_brightness_mode 0 | Out-Null
foreach ($r in @(@('A-off','off'), @('A-on','balanced'), @('B-off','off'), @('B-on','balanced'))) {
  adb shell dumpsys gfxinfo com.instagram.android reset | Out-Null
  $samp = $null
  if ($r[1] -ne 'off') { $samp = Start-Process uv -ArgumentList 'run','--locked','python','-m','workshop.perf.smooth.sample','--minutes','30' -PassThru -NoNewWindow }
  Step "session $($r[0])" { uv run --locked python -m workshop.perf.battery.session --label $r[0] --mode $r[1] --minutes 30 --brightness $Brightness --runs $runs }
  adb shell dumpsys gfxinfo com.instagram.android | Out-File (Join-Path $ev "gfxinfo_$($r[0]).txt") -Encoding utf8
  if ($samp) { $samp.WaitForExit(120000) | Out-Null }
}
Step 'latency capture' { uv run --locked python -m workshop.perf.latency.capture --minutes 5 }
Step 'kills' { uv run --locked python -m workshop.perf.smooth.kill --times 5 }
foreach ($r in @(@('light','light',30), @('strict','strict',30), @('video15','balanced',15))) {
  Step "session $($r[0])" { uv run --locked python -m workshop.perf.battery.session --label $r[0] --mode $r[1] --minutes $r[2] --brightness $Brightness --runs $runs }
}
adb shell settings put system screen_brightness_mode 1 | Out-Null
Step 'battery section' { uv run --locked python -c "import json,sys;from pathlib import Path;from workshop.perf.battery import stats;stats.build_section(json.loads(Path(sys.argv[1]).read_text('utf-8'))).write(Path(sys.argv[2]))" $runs (Join-Path $ev 'battery.json') }
$stamp = (Get-ChildItem data\ch5\perf -Directory | Sort-Object Name | Select-Object -Last 1).FullName
Step 'latency section' { uv run --locked python -m workshop.perf.latency.parse --debug "$stamp\debug.jsonl" --feed "$stamp\feedlog.jsonl" --out (Join-Path $ev 'latency.json') }
Step 'smooth section' { uv run --locked python -m workshop.perf.smooth.section --dir $stamp --out (Join-Path $ev 'smooth.json') }
Step 'report' { uv run --locked python -m workshop.perf.report --evidence $ev --out docs\reports\ch5-guard.md }
$gate = Select-String -Path docs\reports\ch5-guard.md -Pattern '^Gate: (\S+)' | Select-Object -First 1
if ($script:failed) { Done 'FAIL' }
if ($gate -and $gate.Matches[0].Groups[1].Value -eq 'PASS') { Done 'PASS' }
if ($gate -and $gate.Matches[0].Groups[1].Value -eq 'FAIL') { Done 'FAIL' }
Done 'PENDING'
