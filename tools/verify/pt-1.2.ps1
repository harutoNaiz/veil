# Proof test PT-1.2 "Blind label audit", machine part (SPEC section 5).
# Run from the repo root after 1.2.1, 1.2.2 and 1.2.3 pass:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-1.2.ps1
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false

$pt = 'data\synth\pt'
$out = "$pt\out"
$truth = "$pt\truth.json"

# Run a command, print one line, remember a failure. $want is the expected exit code.
function Step([string]$name, [int]$want, [scriptblock]$body) {
  $text = & $body 2>&1 | ForEach-Object { "$_" }
  $code = $LASTEXITCODE
  $ok = ($code -eq $want)
  if (-not $ok) { $text | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ("{0}  {1} (exit {2})" -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name, $code)
  if (-not $ok) { $script:failed = $true }
  return $text
}

# Run a Python snippet from stdin; extra arguments become sys.argv[1:]. Exit 1 on a failed assert.
function Py([string]$code, [string[]]$pyargs) {
  $code | uv run python - @pyargs
}

if (Test-Path $pt) { Remove-Item -Recurse -Force $pt }

Step 'synth 75 + 2 near-dupes into data/synth/pt' 0 {
  uv run python -m workshop.screens.synth --out $pt --n 75 --near-dupes 2
} | Out-Null
New-Item -ItemType Directory -Force $out | Out-Null

Step 'labels.check on truth: LABELS OK' 0 {
  uv run python -m workshop.labels.check --labels $truth --screens $pt
} | Out-Null

Step 'to-ls with truth as prelabels' 0 {
  uv run python -m workshop.labels.ls_convert to-ls --screens $pt --url-prefix '/data/local-files/?d=synth/pt/' `
    --prelabels $truth --out "$out\tasks.json"
} | Out-Null

Step 'from-ls --accept-predictions' 0 {
  uv run python -m workshop.labels.ls_convert from-ls --export "$out\tasks.json" --screens $pt `
    --labeller synth --accept-predictions --out "$out\blind.json"
} | Out-Null

Step 'agree compare truth vs round-tripped labels: rate 0, pass' 0 {
  uv run python -m workshop.labels.agree compare --official $truth --blind "$out\blind.json" --out "$out\agree0.json"
} | Out-Null
Step '  agree report: rate 0, disagreements 0, coverage 1' 0 {
  Py @'
import json, sys
r = json.load(open(sys.argv[1]))
assert r['rate'] == 0 and r['disagreements'] == 0 and r['coverage'] == 1 and r['pass'] is True, r
'@ @("$out\agree0.json")
} | Out-Null

Step 'drop one box from a copy of truth' 0 {
  Py @'
import json, sys
labels = json.load(open(sys.argv[1]))
n = sum(len(x['boxes']) for x in labels)
victim = next(x for x in labels if len(x['boxes']) >= 2)
victim['boxes'].pop()
json.dump(labels, open(sys.argv[2], 'w'))
json.dump({'boxes': n}, open(sys.argv[3], 'w'))
'@ @($truth, "$out\dropped.json", "$out\nboxes.json")
} | Out-Null
Step 'agree compare with 1 box dropped: rate = 1/items (still pass)' 0 {
  uv run python -m workshop.labels.agree compare --official $truth --blind "$out\dropped.json" --out "$out\agree1.json"
} | Out-Null
Step '  agree report: 1 disagreement, items = number of truth boxes, rate = 1/items' 0 {
  Py @'
import json, sys
r = json.load(open(sys.argv[1]))
n = json.load(open(sys.argv[2]))['boxes']
assert r['disagreements'] == 1 and r['items'] == n and abs(r['rate'] - 1 / n) < 1e-12, (r, n)
'@ @("$out\agree1.json", "$out\nboxes.json")
} | Out-Null

Step 'split (seed 12): every concept and app within 60 +/- 5, no cluster straddles' 0 {
  uv run python -m workshop.eval.split --labels $truth --screens $pt --seed 12 --out "$out\splits.json"
} | Out-Null
Step 'dupes: no near-dupe pair straddles dev/test' 0 {
  uv run python -m workshop.eval.dupes --screens $pt --splits "$out\splits.json"
} | Out-Null
Step '  both near-dupe pairs are clustered and sit on one side' 0 {
  Py @'
import json, sys
s = json.load(open(sys.argv[1]))
pairs = [g for g in s['clusters'] if any(n.endswith('-dup.png') for n in g)]
assert len(pairs) == 2, s['clusters']
for g in pairs:
    assert all(n in s['dev'] for n in g) or all(n in s['test'] for n in g), g
'@ @("$out\splits.json")
} | Out-Null

Copy-Item docs\datasets.md "$out\datasets-temp.md" -Force
$fz = @('--screens', $pt, '--labels', $truth, '--splits', "$out\splits.json", '--doc', "$out\datasets-temp.md")
Step 'freeze write to a temp doc' 0 { uv run python -m workshop.eval.freeze write @fz } | Out-Null
Step 'freeze check ok' 0 { uv run python -m workshop.eval.freeze check @fz } | Out-Null
$flip = @'
import json, sys
name = json.load(open(sys.argv[1]))['test'][0]
p = sys.argv[2] + '/' + name
b = bytearray(open(p, 'rb').read())
b[len(b) // 2] ^= 0xFF
open(p, 'wb').write(bytes(b))
'@
Py $flip @("$out\splits.json", $pt) | Out-Null
Step 'freeze check after tampering one test PNG byte fails' 1 { uv run python -m workshop.eval.freeze check @fz } | Out-Null
Py $flip @("$out\splits.json", $pt) | Out-Null   # flip back: the PNG is restored
Step 'freeze check after restoring the byte is ok again' 0 { uv run python -m workshop.eval.freeze check @fz } | Out-Null

foreach ($kind in 'perfect', 'empty', 'mistakes') {
  Step "fake_preds $kind" 0 {
    uv run python -m workshop.eval.fake_preds $kind --labels $truth --seed 1 --out "$out\preds-$kind.json"
  } | Out-Null
  Step "score_screens $kind" 0 {
    uv run python -m workshop.eval.score_screens --labels $truth --preds "$out\preds-$kind.json" --out "$out\score-$kind.json"
  } | Out-Null
}
Step '  scores: perfect 1.0 / 1.0 / 0, empty recall 0, mistakes (C-2)/C, (C-2)/C, 2/K' 0 {
  Py @'
import json, sys
d = sys.argv[1]
truth = json.load(open(sys.argv[2]))
C = sum(1 for x in truth for b in x['boxes'] if b['concept'] == 'cats')
K = sum(1 for x in truth if x['clean'])
def load(k):
    return json.load(open(f'{d}/score-{k}.json'))
def near(a, b):
    return abs(a - b) < 1e-9
p = load('perfect')
for c in p['concepts'].values():
    assert c['recall'] == 1.0 and c['precision'] == 1.0 and c['cleanFalseCover'] == 0, p
assert p['cleanFalseCover'] == 0
e = load('empty')
for c in e['concepts'].values():
    assert c['recall'] == 0 and c['cleanFalseCover'] == 0, e
assert e['cleanFalseCover'] == 0
m = load('mistakes')
cats, spiders = m['concepts']['cats'], m['concepts']['spiders']
assert near(cats['recall'], (C - 2) / C), (cats, C)
assert near(cats['precision'], (C - 2) / C), (cats, C)
assert near(m['cleanFalseCover'], 2 / K), (m, K)
assert spiders['recall'] == 1.0, spiders
'@ @($out, $truth)
} | Out-Null

Write-Host '--- counts (informational: the synthetic set is below the real-set thresholds) ---'
Step 'counts prints' 0 { uv run python -m workshop.eval.counts --labels $truth } | ForEach-Object { Write-Host "    $_" }

if ($failed) { Write-Host 'PT-1.2 MACHINE: FAIL'; exit 1 }
Write-Host 'PT-1.2 MACHINE: PASS'
exit 0
