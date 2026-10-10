"""Diagnostics for phone_eval: which pieces fire on clean screens (source, size, flatness)."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from workshop.twin import phone_eval as pe
from workshop.twin.judge import judge
from workshop.twin.pieces import crop


def main(path: str, mode: str) -> None:
    cc = json.loads(Path(path).read_text(encoding="utf-8"))
    screens = pe.load_screens()
    emb, _ = pe.embed(screens)
    src, rows = Counter(), []
    for s, (regions, vecs, _t) in zip(screens, emb, strict=True):
        if not (s.label or {}).get("clean"):
            continue
        img = Image.open(s.image).convert("L")
        for r, v in zip(regions, judge(vecs, cc, mode), strict=True):
            if v["decision"] != "hide":
                continue
            c = np.asarray(crop(img, r["rect"]), dtype=np.float64)
            rows.append(
                (
                    s.image.name,
                    r["source"],
                    r["rect"]["w"],
                    r["rect"]["h"],
                    round(c.std(), 1),
                    round(v["score"], 3),
                    round(v["margin"], 3),
                )
            )
            src[r["source"]] += 1
    print(src)
    for row in rows[:80]:
        print(row)
    print(len(rows))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
