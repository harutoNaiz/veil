# Verify sub-phase 1.3.2 "Add the object finder". Run from anywhere:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\1.3.2.ps1
# Ends with VERIFY 1.3.2: PASS, or PASS-PENDING-WEIGHTS when only checks that need the SigLIP2 weights
# (variants A and C, the Describer list switch) or the 1.3.1 modules are still missing.
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
  $script:out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $script:out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

$mine = @('workshop/twin/finder.py', 'workshop/twin/variants.py', 'workshop/twin/tests/test_finder.py')

# --- what is available yet -----------------------------------------------------------------------
$hub = Join-Path $env:HF_HOME 'hub\models--google--siglip2-base-patch16-224'
$pending = @()
if (-not (Test-Path "$hub\snapshots\*\model.safetensors")) { $pending += 'SigLIP2 model.safetensors' }
if (Test-Path "$hub\blobs") {
  # a stale *.incomplete (untouched for 10+ min, left by an old attempt) is not an active download
  $active = @(Get-ChildItem "$hub\blobs" -Filter *.incomplete -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-10) })
  if ($active.Count -gt 0) { $pending += 'SigLIP2 download still active (*.incomplete)' }
}
$need = 'data', 'describer', 'pieces', 'teacher', 'judge', 'run'
$missingMods = @($need | Where-Object { -not (Test-Path "workshop/twin/$_.py") })
if ($missingMods.Count -gt 0) { $pending += "1.3.1 modules not written yet: $($missingMods -join ', ')" }
$yoloe = (Test-Path 'data\models\yoloe-26s-seg.pt') -and (Test-Path 'data\models\mobileclip*')
$siglipPending = ($pending.Count -gt 0)

Check '(1) ruff check + format check on the 1.3.2 files' {
  uv run ruff check @mine
  if ($LASTEXITCODE -eq 0) { uv run ruff format --check @mine }
}

if ($yoloe) {
  Check '(2) pytest test_finder: valid boxes, normalised vectors, B on a few images, list switch, chooser' {
    uv run pytest workshop/twin/tests/test_finder.py -q -rs
  }
  $skips = @($script:out | Where-Object { $_ -match '^SKIPPED' })
  $skips | ForEach-Object { Write-Host "    $_" }
  if (-not $siglipPending -and @($skips | Where-Object { $_ -match '1\.3\.1 modules|SigLIP2' }).Count -gt 0) {
    Write-Host 'FAIL  a SigLIP2 / 1.3.1 test was skipped although everything is present'
    $script:failed = $true
  }
} else {
  Write-Host 'skip  (2) pytest: YOLOE weights (data\models\yoloe-26s-seg.pt, mobileclip*) missing'
  $pending += 'YOLOE weights'
}

# --- variants CLI (needs the 1.3.1 modules; A and C also need SigLIP2) ---------------------------
$py = Join-Path $env:TEMP 'veil-verify-132.py'
Set-Content -Path $py -Encoding utf8 -Value @'
import json, sys
full = sys.argv[1] == "full"
d = json.load(open(f"data/ch1/variants-{sys.argv[2]}.json", encoding="utf-8"))
rows = d["rows"]
for v in "ABC":
    assert any(r["variant"] == v for r in rows), f"no rows for {v}"
def num(r):
    return all(r[k] is not None and 0 <= r[k] <= 1 for k in ("recall", "precision", "cleanFalseCover"))
for r in rows:
    assert num(r) or r["note"].startswith("not run:"), r
if full:
    for v in "AC":
        assert all(num(r) for r in rows if r["variant"] == v), f"{v} has no numbers"
    assert d["chosen"] in ("A", "B", "C") and d["reason"], "chosen not set"
elif any(num(r) for r in rows):
    assert d["chosen"] in ("A", "B", "C") and d["reason"], "chosen not set"
print("variants rows:", len(rows), "chosen:", d["chosen"])
print(d["reason"])
'@
if ($missingMods.Count -eq 0 -and $yoloe) {
  $mode = if ($siglipPending) { 'partial' } else { 'full' }
  Check "(3) variants CLI synthetic/dev cats,spiders writes variants-synthetic.json ($mode)" {
    Remove-Item 'data\ch1\variants-synthetic.json' -ErrorAction SilentlyContinue
    uv run python -m workshop.twin.variants --set synthetic --split dev --concepts cats,spiders
    if ($LASTEXITCODE -ne 0) { return }
    uv run python $py $mode synthetic
  }
  $script:out | Where-Object { $_ -match '^\|' -or $_ -match '^chosen' -or $_ -match 'variants rows' } | ForEach-Object { Write-Host "    $_" }
} else {
  Write-Host 'skip  (3) variants CLI: 1.3.1 modules or YOLOE weights missing'
}

if ($missingMods.Count -eq 0 -and $yoloe -and (Test-Path 'data\public\set')) {
  Check "(3b) variants CLI public/dev (A1 real-photo set) cats,spiders ($mode)" {
    Remove-Item 'data\ch1\variants-public.json' -ErrorAction SilentlyContinue
    uv run python -m workshop.twin.variants --set public --split dev --concepts cats,spiders
    if ($LASTEXITCODE -ne 0) { return }
    uv run python $py $mode public
  }
  $script:out | Where-Object { $_ -match '^\|' -or $_ -match '^chosen' -or $_ -match 'variants rows' } | ForEach-Object { Write-Host "    $_" }
}

Check '(4) git: weights are ignored and no *.pt / *.ts file shows in status' {
  $bad = @(git status --porcelain | Where-Object { $_ -match '\.(pt|ts)"?$' })
  if ($bad.Count -gt 0) { $bad | ForEach-Object { Write-Output "tracked weight file: $_" }; $global:LASTEXITCODE = 1; return }
  git check-ignore -q some/dir/x.pt
  if ($LASTEXITCODE -ne 0) { Write-Output '*.pt not ignored'; return }
  git check-ignore -q some/dir/mobileclip2_b.ts
  if ($LASTEXITCODE -ne 0) { Write-Output 'mobileclip*.ts not ignored'; return }
  $global:LASTEXITCODE = 0
}

if ($script:failed) { Write-Host 'VERIFY 1.3.2: FAIL'; exit 1 }
if ($pending.Count -gt 0) {
  Write-Host "WEIGHTS PENDING: $($pending -join '; ')"
  Write-Host 'skipped or partial: variants A and C numbers, Describer list switch, chosen variant over all three'
  Write-Host 'VERIFY 1.3.2: PASS-PENDING-WEIGHTS'
  exit 0
}
Write-Host 'VERIFY 1.3.2: PASS'
exit 0
