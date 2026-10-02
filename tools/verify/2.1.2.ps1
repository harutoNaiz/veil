# Verify sub-phase 2.1.2 "Label recordings".
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

Step '1 pytest recordings' { uv run pytest workshop/labels/tests/test_recordings.py -q }
Step '2 from-ls CLI + validate' {
  $tmp = Join-Path $env:TEMP 'veil-212-label.json'
  uv run python -m workshop.labels.recordings from-ls workshop/labels/tests/fixtures/ls-video-export.json workshop/labels/tests/fixtures/ls-video-session.json --out $tmp
  if ($LASTEXITCODE -eq 0) { uv run python -m workshop.labels.recordings validate $tmp }
}
Step '3 ruff' { uv run ruff check workshop/labels/recordings.py workshop/labels/tests/test_recordings.py }

if ($script:failed) { Write-Host 'VERIFY 2.1.2: FAIL'; exit 1 }
Write-Host 'VERIFY 2.1.2: PASS'
exit 0
