"""Laptop reference fingerprints for the phone parity check (3.3).

Copies the first N sorted PNGs of data/public/set into data/ch3/phone/screens/ and writes
laptop-fp.csv (image, v0..v767) from siglip2-image-b1.onnx on CPU.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image

from workshop.forge.siglip2.runtime import DIM, OnnxDescriber

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data" / "public" / "set"
OUT = ROOT / "data" / "ch3" / "phone"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    pngs = sorted(SRC.glob("*.png"))[: args.limit]
    screens = OUT / "screens"
    screens.mkdir(parents=True, exist_ok=True)
    for p in pngs:
        shutil.copy2(p, screens / p.name)
    describer = OnnxDescriber()
    lines = []
    for p in pngs:
        with Image.open(p) as im:
            vec = describer.embed_images([im.copy()], batch=1)[0]
        assert len(vec) == DIM
        lines.append(p.name + "," + ",".join(f"{float(v):.6f}" for v in vec))
    header = "image," + ",".join(f"v{i}" for i in range(DIM))
    (OUT / "laptop-fp.csv").write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} rows of {DIM} to {OUT / 'laptop-fp.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
