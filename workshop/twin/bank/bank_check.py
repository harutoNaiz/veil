"""Re-embed a seeded sample of bank rows and check them, plus licences (AC-05)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from workshop.twin.bank import bankio, coco, engine, ui_synth
from workshop.twin.bank.build_bank import ONNX, ROOT


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--sample", type=int, default=64)
    ap.add_argument("--engine", choices=["torch", "onnx"], default="torch")
    ap.add_argument("--provider", choices=["cpu", "dml"], default="cpu")
    a = ap.parse_args(argv)
    d = Path(a.bank)
    if not d.is_absolute():
        d = ROOT / d
    items = [json.loads(x) for x in (d / "items.jsonl").read_text(encoding="utf-8").splitlines()]
    bank = bankio.read_bank(d / "bank.bin")
    assert len(items) == len(bank.rows)
    good = sum(
        1
        for it in items
        if (it["source"] == "coco" and it["licenseId"] in coco.LICENCES)
        or (it["source"] == "ui" and it["license"] == ui_synth.LICENCE)
    )
    print(f"LICENCES ok={good}/{len(items)}")
    if good != len(items):
        return 1
    rng = np.random.default_rng(7)
    pick = sorted(rng.choice(len(items), size=min(a.sample, len(items)), replace=False).tolist())
    imgs, rows = [], []
    for i in pick:
        it = items[i]
        im = (
            coco.fetch_image(it["url"])
            if it["source"] == "coco"
            else ui_synth.render_screen(int(it["id"].split("-")[1]))
        )
        if im is not None:
            imgs.append(im)
            rows.append(i)
    v = engine.make_describer(a.engine, a.provider, ONNX).embed_images(imgs).astype(np.float64)
    cos = (v * bank.rows[rows]).sum(axis=1)
    mc = float(cos.min())
    print(f"BANK_CHECK min_cos={mc:.5f} n={len(rows)}")
    return 0 if mc >= 0.999 else 1


if __name__ == "__main__":
    raise SystemExit(main())
