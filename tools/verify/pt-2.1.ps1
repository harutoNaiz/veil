# Proof test PT-2.1 "Known scroll replay" (machine part). Needs 2.1.1's synthetic generator.
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-2.1.ps1
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Step([string]$name, [scriptblock]$body, [int]$expect = 0) {
  & $body | Out-Host
  $code = $LASTEXITCODE
  if ($code -eq $expect) { Write-Host "ok    $name" }
  else { Write-Host "FAIL  $name (exit $code, wanted $expect)"; $script:failed = $true }
}

$ev = 'data/evidence/pt-2.1'
$sess = "$ev/session"
$sid = 'synth-known-scroll'
$sj = "$sess/$sid.session.json"
if (Test-Path $ev) { Remove-Item -Recurse -Force $ev }
New-Item -ItemType Directory -Force $sess | Out-Null

Step '1 synth_session 60 s' { uv run python -m workshop.recordings.synth_session --out $sess --seconds 60 }
Step '2a sync_check PASS at offset 0' { uv run python -m workshop.recordings.sync_check $sj }
$off = "$ev/offset100"
Step '2b sync_check FAIL at +100 ms' { uv run python -m workshop.recordings.synth_session --out $off --seconds 20 --event-offset-ms 100; uv run python -m workshop.recordings.sync_check "$off/$sid.session.json" } 1
foreach ($n in 1, 2, 3) {
  Step "3.$n replay oracle --markers" { uv run python -m workshop.replay $sj --out "$ev/run$n" --pipeline oracle --markers }
}
$lines = foreach ($n in 1, 2, 3) {
  foreach ($k in 'tape-in', 'tape-out') { $f = "$ev/run$n/$sid.$k.jsonl"; "{0} {1} {2}" -f $n, $k, (Get-FileHash $f -Algorithm SHA256).Hash }
}
$lines | Set-Content "$ev/hashes.txt" -Encoding ascii
$bad = 0
foreach ($k in 'tape-in', 'tape-out') {
  $h = @(1, 2, 3 | ForEach-Object { (Get-FileHash "$ev/run$_/$sid.$k.jsonl" -Algorithm SHA256).Hash } | Select-Object -Unique)
  if ($h.Count -ne 1) { $bad++ }
}
if ($bad) { Write-Host 'FAIL  4 hashes differ'; $script:failed = $true } else { Write-Host 'ok    4 three replays byte-identical' }
Step '5 scroll totals match driver' { uv run python -c "
import json, sys
from pathlib import Path
from workshop.replay.checks import bursts, scroll_totals
drv = json.loads(Path('$sess/$sid.driver.json').read_text())
want = bursts([(d['tMs'], d['dy']) for d in drv if d['dy'] != 0])
got = scroll_totals(Path('$ev/run1/$sid.tape-in.jsonl'))
print('bursts', len(got))
sys.exit(0 if got == want and len(got) > 0 else 1)
" }
Step '6 self-capture error <= 1' { uv run python -m workshop.replay.checks self-capture $sj }
Step '7 replay --self-capture' { uv run python -m workshop.replay $sj --out "$ev/selfcap" --pipeline oracle --self-capture --no-video }
Step '8 tape validate' { uv run python -m workshop.replay.tape validate "$ev/run1/$sid.tape-in.jsonl" "$ev/run1/$sid.tape-out.jsonl" "$ev/selfcap/$sid.tape-in.jsonl" "$ev/selfcap/$sid.tape-out.jsonl" }
Step '9 recording label validates' { uv run python -m workshop.labels.recordings validate "$sess/labels/$sid.json" }
Copy-Item "$ev/run1/$sid.covered.mp4" "$ev/marked.covered.mp4" -ErrorAction SilentlyContinue
Copy-Item "$sess/$sid.sync.csv" "$ev/sync.csv" -ErrorAction SilentlyContinue

if ($script:failed) { Write-Host 'PT 2.1: FAIL'; exit 1 }
Write-Host 'PT 2.1: PASS'
