# Verify D-text-dml: SigLIP2 text encoder on DirectML matches CPU (cosine >= 0.999) + timing.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$env:HF_HUB_OFFLINE = '1'
$py = Join-Path $env:TEMP 'veil_d_text_dml.py'
@'
import time, gc
from pathlib import Path
import numpy as np
from workshop.twin.bank.engine import make_describer
ONNX = Path("data/forge/siglip2")
words = ["cat","dog","a photo of a red car","mountain lake","person riding a bicycle","bowl of soup","violin","skyscraper at night"]
texts = [f"{w} {i}" if i % 2 else w for i in range(4) for w in words]
res = {}
for prov in ("cpu", "dml"):
    d = make_describer("onnx", prov, ONNX)
    d.embed_texts(texts[:2])
    t = time.time(); e = d.embed_texts(texts); dt = time.time() - t
    res[prov] = e
    print(f"{prov}: {len(texts)/dt:.2f} texts/s")
    del d; gc.collect()
cos = (res["cpu"] * res["dml"]).sum(1) / (np.linalg.norm(res["cpu"], axis=1) * np.linalg.norm(res["dml"], axis=1))
print(f"cosine min={cos.min():.6f} max={cos.max():.6f} n={len(cos)}")
raise SystemExit(0 if cos.min() >= 0.999 else 1)
'@ | Set-Content -Encoding utf8 $py
# fallback (uv --with fails on this box): scratch DML build via PYTHONPATH over .venv python
$env:PYTHONPATH = "$repo;$env:VEIL_TOOLCHAIN\cache\ort-dml"
& "$repo\.venv\Scripts\python.exe" $py
if ($LASTEXITCODE -eq 0) { 'VERIFY D-text-dml: PASS' } else { 'VERIFY D-text-dml: FAIL'; exit 1 }
