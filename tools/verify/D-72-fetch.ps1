# Verify D-72-fetch: bench fetch works for Flickr URLs.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false
$tmp = Join-Path $env:TEMP ("d72fetch_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
$py = Join-Path $tmp 'chk.py'
@'
import json, sys
from pathlib import Path
from workshop.twin.bench import fetch_embed
sel = json.load(open("data/bench/mini/selection.json", encoding="utf-8"))
cache = Path(sys.argv[1])
# some Flickr images are gone (410); bench has spares. Need 3 ok out of the first 10.
res = [fetch_embed.fetch_one(sel["images"][i], cache) for i in list(sel["images"])[:10]]
print([(r["id"], r["ok"]) for r in res])
sys.exit(0 if sum(r["ok"] for r in res) >= 3 else 1)
'@ | Set-Content -Encoding utf8 $py
uv run --locked python $py $tmp | Out-Host
if ($LASTEXITCODE -ne 0) { Write-Host 'FAIL fetch 3'; $failed = $true }
if (Test-Path 'workshop\twin\bench\tests') {
  uv run --locked pytest workshop/twin/bench/tests -q | Out-Host
  if ($LASTEXITCODE -ne 0) { Write-Host 'FAIL pytest'; $failed = $true }
}
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
if ($failed) { Write-Host 'VERIFY D-72-fetch: FAIL'; exit 1 } else { Write-Host 'VERIFY D-72-fetch: PASS' }
