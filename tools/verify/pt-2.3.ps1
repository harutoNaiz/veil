# Proof test PT-2.3 machine part: "Watch it like a user". Ends with PT-2.3 machine: PASS|FAIL.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false
uv run python -c "from workshop.twin.motion_synth import ensure_test_set; ensure_test_set('data/ch2/synth-test')"
$dir = 'data/ch2/synth-test'
$ev = 'D:\iqoo finale\progress\ch2-motion\phase-2.3-steady-covers\evidence\pt-2.3'
New-Item -ItemType Directory -Force $ev | Out-Null
$sess = @("$dir/synth-test-3.session.json", "$dir/synth-test-4.session.json", "$dir/torture-22.session.json")
uv run python -m workshop.twin.motion eval --sessions @sess --out data/ch2/pt-2.3 --modes balanced --video balanced
if ($LASTEXITCODE -ne 0) { $failed = $true }
foreach ($id in 'synth-test-3', 'synth-test-4', 'torture-22') {
  $f = "data/ch2/pt-2.3/balanced/$id.sbs.mp4"
  if (Test-Path $f) { Copy-Item $f $ev -Force } else { Write-Host "FAIL missing $f"; $failed = $true }
}
uv run python -m workshop.eval.score_motion marks-csv "$ev\marks-machine.csv" data/ch2/pt-2.3 @sess
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run python -m workshop.eval.score_motion check-pt data/ch2/pt-2.3/scores.json torture-22
if ($LASTEXITCODE -ne 0) { $failed = $true }
uv run python -m workshop.twin.motion eval --sessions "$dir/torture-22.session.json" --out data/ch2/pt-2.3-ruleoff --modes balanced --rule off --video none | Out-Null
uv run python -m workshop.eval.score_motion print-flicker data/ch2/pt-2.3-ruleoff/scores.json torture-22
if ($failed) { Write-Host 'PT-2.3 machine: FAIL'; exit 1 }
Write-Host 'PT-2.3 machine: PASS'
