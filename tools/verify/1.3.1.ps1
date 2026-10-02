# Verify sub-phase 1.3.1 "Describer and Judge on whole pieces". Run from anywhere:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\1.3.1.ps1
# Ends with VERIFY 1.3.1: PASS, or PASS-PENDING-WEIGHTS when everything else passes but the SigLIP2
# weights are not in the local cache yet (the model checks then print WEIGHTS PENDING and are skipped).
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$env:HF_HUB_OFFLINE = '1'
$env:YOLO_AUTOINSTALL = 'False'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

$mine = @(
  'workshop/twin/__init__.py', 'workshop/twin/data.py', 'workshop/twin/describer.py',
  'workshop/twin/pieces.py', 'workshop/twin/teacher.py', 'workshop/twin/judge.py',
  'workshop/twin/run.py', 'workshop/twin/gallery.py', 'workshop/twin/public_set.py',
  'workshop/twin/tests/test_twin_v0.py', 'workshop/twin/tests/test_public_set.py'
)

Check '(1) ruff check + format check on the 1.3.1 files' {
  uv run ruff check @mine
  if ($LASTEXITCODE -eq 0) { uv run ruff format --check @mine }
}

Check '(2) pytest: cards, Judge (hide / nearMiss / leave, margin rule), pieces 1+18+3, Findings, test-run guard, stub pipeline, public set' {
  uv run pytest workshop/twin/tests/test_twin_v0.py workshop/twin/tests/test_public_set.py -q
}

$weights = (uv run python -c "from workshop.twin.describer import weights_available as w; print(int(w()))" 2>$null | Select-Object -Last 1)
$pending = ($weights -ne '1')
if ($pending) {
  Write-Host 'WEIGHTS PENDING  SigLIP2 is not complete in the HF cache: describer smoke and the CLI run are skipped'
} else {
  Check '(3) Describer smoke: embed_texts is (1, 768) with norm 1 (inside pytest test_describer_smoke, which must not skip)' {
    $r = uv run pytest workshop/twin/tests/test_twin_v0.py -q -k describer_smoke -rs 2>&1 | ForEach-Object { "$_" }
    $r | Select-Object -Last 3 | ForEach-Object { Write-Output $_ }
    if (-not ($r -match '1 passed')) { $global:LASTEXITCODE = 1 }
  }

  $check = @'
import json, os, subprocess, sys
from pathlib import Path

def run(args):
    p = subprocess.run([sys.executable, "-m", "workshop.twin.run", *args], capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-1500:]); sys.exit(1)
    return json.loads(p.stdout)

def frac(x):
    return isinstance(x, (int, float)) and 0 <= x <= 1

sets = ["synthetic"] + (["public"] if Path("data/public/set/truth.json").is_file() else [])
for name in sets:
    r = run(["--set", name, "--split", "dev", "--concepts", "cats,spiders", "--variant", "A", "--gallery"])
    for c in ("cats", "spiders"):
        s = r[c]
        ok = frac(s["recall"]) and frac(s["cleanFalseCover"]) and (frac(s["precision"]) or (s["precision"] is None and s["covers"] == 0))
        print(name, c, {k: (round(s[k], 3) if isinstance(s[k], float) else s[k]) for k in ("recall", "precision", "cleanFalseCover", "covers", "labels")})
        if not ok:
            print("score out of range"); sys.exit(1)
    html = Path(r["gallery"]).read_text(encoding="utf-8")
    if html.count("<img") < 1:
        print("gallery has no <img>"); sys.exit(1)
    print(name, "secPerScreen", round(r["secPerScreen"], 2), "gallery", r["gallery"], "imgs", html.count("<img"))
'@
  Check '(4) CLI variant A on the dev splits (synthetic, and public if built): scores in [0,1], gallery index.html has <img>' {
    $check | uv run python -
  }
}

if ($script:failed) { Write-Host 'VERIFY 1.3.1: FAIL'; exit 1 }
if ($pending) { Write-Host 'VERIFY 1.3.1: PASS-PENDING-WEIGHTS'; exit 0 }
Write-Host 'VERIFY 1.3.1: PASS'
exit 0
