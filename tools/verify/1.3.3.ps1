# Verify sub-phase 1.3.3 "Tune, analyse, decide". Run from anywhere:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\1.3.3.ps1
# Ends with VERIFY 1.3.3: PASS, or PASS-PENDING-WEIGHTS when the SigLIP2 / YOLOE weights or the 1.3.1 / 1.3.2
# modules are not all present yet (the end-to-end part is then skipped; the orchestrator re-runs this later).
param([int]$Only = 0)   # run just check number N (e.g. -Only 8); 0 = everything
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$env:HF_HUB_OFFLINE = '1'
$env:YOLO_AUTOINSTALL = 'False'
$script:failed = $false
$script:out = @()

function Check([string]$name, [scriptblock]$body) {
  $num = [int]([regex]::Match($name, '^\((\d+)\)').Groups[1].Value)
  if ($Only -gt 0 -and $num -ne $Only) { return }
  $script:out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $script:out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

$mine = @('workshop/twin/calibrate.py', 'workshop/twin/report.py', 'workshop/twin/tests/test_calibrate.py')
$ch1 = Join-Path $repo 'data\ch1'

Check '(1) ruff check + format check on the 1.3.3 files' {
  uv run ruff check @mine
  if ($LASTEXITCODE -eq 0) { uv run ruff format --check @mine }
}

Check '(2) pytest test_calibrate: offset formula, threshold order, decision block replaced not duplicated' {
  uv run pytest workshop/twin/tests/test_calibrate.py -q
}

Check '(3) wiring: report and calibrate CLIs start, ch1_see.ps1 parses, JSON files parse' {
  uv run python -m workshop.twin.report --help | Out-Null
  if ($LASTEXITCODE -ne 0) { return }
  uv run python -m workshop.twin.calibrate compare --help | Out-Null
  if ($LASTEXITCODE -ne 0) { return }
  $errs = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile("$repo\tools\ch1_see.ps1", [ref]$null, [ref]$errs)
  if ($errs.Count -gt 0) { $errs | ForEach-Object { Write-Output "parse: $_" }; $global:LASTEXITCODE = 1; return }
  uv run python -c "import json; json.load(open('workshop/twin/calibration.json')); m=json.load(open('workshop/twin/thresholds.json'))['modes']; assert m['light']>=m['balanced']>=m['strict']"
}

# --- end-to-end part: needs 1.3.1 / 1.3.2 code and the downloaded weights --------------------------
$need = 'data', 'describer', 'pieces', 'teacher', 'judge', 'run', 'gallery', 'finder', 'variants'
$missingMods = @($need | Where-Object { -not (Test-Path "workshop/twin/$_.py") })

$hub = Join-Path $env:HF_HOME 'hub\models--google--siglip2-base-patch16-224'
$pending = @()
if ($missingMods.Count -gt 0) { $pending += "1.3.1 / 1.3.2 modules not there yet: $($missingMods -join ', ')" }
if (-not (Test-Path "$hub\snapshots\*\model.safetensors")) { $pending += 'SigLIP2 model.safetensors' }
if (Test-Path "$hub\blobs") {
  if (@(Get-ChildItem "$hub\blobs" -Filter *.incomplete -ErrorAction SilentlyContinue).Count -gt 0) { $pending += 'SigLIP2 download still has *.incomplete' }
}
if (-not (Test-Path 'data\models\yoloe-*seg.pt')) { $pending += 'YOLOE yoloe-*seg.pt' }
if (-not (Test-Path 'data\models\mobileclip*')) { $pending += 'YOLOE text encoder mobileclip*' }
if (@(Get-ChildItem 'data\models' -Include *.part, *.tmp, *.download -Recurse -ErrorAction SilentlyContinue).Count -gt 0) { $pending += 'partial download in data\models' }

if ($script:failed) {
  Write-Host 'VERIFY 1.3.3: FAIL'; exit 1
}
if ($pending.Count -gt 0) {
  Write-Host "WEIGHTS PENDING: $($pending -join '; ')"
  Write-Host 'skipped: ch1_see.ps1 -Set synthetic -Test, results/report/decision checks, -NoCache rerun, -Fresh smoke'
  Write-Host 'VERIFY 1.3.3: PASS-PENDING-WEIGHTS'
  exit 0
}

$runner = "$repo\tools\ch1_see.ps1"
$n = (uv run python -c "from workshop.twin import calibrate as C; print(C.count_test_runs('synthetic'))") | Select-Object -Last 1
$useTest = ([int]$n -lt 3)
if (-not $useTest) { Write-Host "note  synthetic test budget already used ($n/3): first run goes without -Test" }

Check '(4) ch1_see.ps1 -Set synthetic -Test (cache on)' {
  if ($useTest) { powershell -NoProfile -ExecutionPolicy Bypass -File $runner -Set synthetic -Test }
  else { powershell -NoProfile -ExecutionPolicy Bypass -File $runner -Set synthetic }
}
if ($Only -eq 0) { Copy-Item "$ch1\results-synthetic.json" "$ch1\_verify-first.json" -Force -ErrorAction SilentlyContinue }

Check '(5) calibration/thresholds ordered, AC-1.3-04 ordering, report headings, decision block, <= 3 test runs' {
  uv run python -m workshop.twin.calibrate check --set synthetic
}

Check '(6) -NoCache rerun (no -Test): every number within 0.005 of the first run' {
  powershell -NoProfile -ExecutionPolicy Bypass -File $runner -Set synthetic -NoCache
  if ($LASTEXITCODE -ne 0) { return }
  uv run python -m workshop.twin.calibrate compare "$ch1\_verify-first.json" "$ch1\results-synthetic.json" --tol 0.005
}
# The rerun had no test block: rewrite the outputs from the first run (same numbers, includes the test table).
if ($Only -eq 0) { uv run python -c "import json; from workshop.twin import report as R; R.write_outputs(json.load(open(r'$ch1\_verify-first.json')))" | Out-Null }
Check '(7) outputs consistent after the rewrite' { uv run python -m workshop.twin.calibrate check --set synthetic }

$smoke = Join-Path $ch1 'fresh\_verify-smoke'
New-Item -ItemType Directory -Force $smoke | Out-Null
Get-ChildItem $smoke -File | Remove-Item -Force
Get-ChildItem 'data\synth\1.2.1\*.png' | Select-Object -First 3 | Copy-Item -Destination $smoke
Check '(8) -Fresh smoke on 3 synthetic images: gallery index.html and tally.md exist' {
  $o = @(powershell -NoProfile -ExecutionPolicy Bypass -File $runner -Fresh $smoke -Concepts cats,spiders 2>&1 | ForEach-Object { "$_" })
  if ($LASTEXITCODE -ne 0) { $o | Select-Object -Last 10 | ForEach-Object { Write-Output $_ }; return }
  $g = ($o | Where-Object { $_ -like 'GALLERY: *' } | Select-Object -Last 1) -replace '^GALLERY: ', ''
  $ok = $g -and (Test-Path -LiteralPath $g) -and (Test-Path -LiteralPath (Join-Path (Split-Path $g -Parent) 'tally.md'))
  if (-not $ok) { Write-Output "gallery or tally.md missing (GALLERY line: '$g')" }
  $global:LASTEXITCODE = $(if ($ok) { 0 } else { 1 })
}

if ($script:failed) { Write-Host 'VERIFY 1.3.3: FAIL'; exit 1 }
Write-Host 'VERIFY 1.3.3: PASS'
exit 0
