# Verify sub-phase 2.1.1 "Record sessions". Run from anywhere:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\2.1.1.ps1
# Ends with VERIFY 2.1.1: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
$tmp = Join-Path $env:TEMP ('veil211-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force $tmp | Out-Null
$ok = Join-Path $tmp 'ok'
$bad = Join-Path $tmp 'bad'

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $good = ($LASTEXITCODE -eq 0)
  if (-not $good) { $out | Select-Object -Last 20 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($good) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $good) { $script:failed = $true }
}

Check '(1) ruff check + format check' {
  uv run ruff check workshop/recordings
  if ($LASTEXITCODE -eq 0) { uv run ruff format --check workshop/recordings }
}
Check '(2) pytest workshop/recordings' { uv run pytest workshop/recordings -q }
Check '(3) generate 20 s session (CLI)' { uv run python -m workshop.recordings.synth_session --out $ok }
Check '(4) every events line validates as UiEvent' {
  uv run python -m workshop.contracts.validate --type UiEvent --jsonl (Join-Path $ok 'synth-known-scroll.events.jsonl')
}
Check '(5) working copy 360x800, 600 frames (ffprobe)' {
  $r = ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=width,height,nb_read_frames -of csv=p=0 (Join-Path $ok 'synth-known-scroll.mp4')
  Write-Host "    $r"
  if ($r -ne '360,800,600') { cmd /c exit 1 }
}
Check '(6) sync check PASS at offset 0, FAIL at 100 ms' {
  uv run python -m workshop.recordings.sync_check (Join-Path $ok 'synth-known-scroll.session.json')
  if ($LASTEXITCODE -ne 0) { return }
  uv run python -m workshop.recordings.synth_session --out $bad --seconds 10 --event-offset-ms 100 | Out-Null
  $o = uv run python -m workshop.recordings.sync_check (Join-Path $bad 'synth-known-scroll.session.json')
  Write-Host "    $o"
  if ($LASTEXITCODE -eq 0 -or "$o" -notmatch 'FAIL') { cmd /c exit 1 } else { cmd /c exit 0 }
}
Check '(7) record.py --dry-run prints screenrecord' {
  $o = uv run python -m workshop.recordings.record --name t --seconds 20 --dry-run
  if ("$o" -notmatch 'screenrecord') { cmd /c exit 1 }
}
Check '(8) index reports synthetic situations' {
  $o = uv run python -m workshop.recordings.index $ok
  Write-Host "    $o"
  if ("$o" -notmatch 'slowScroll=2' -or "$o" -notmatch 'lockUnlock=2') { cmd /c exit 1 }
}

Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
if ($script:failed) { Write-Host 'VERIFY 2.1.1: FAIL'; exit 1 }
Write-Host 'VERIFY 2.1.1: PASS'
