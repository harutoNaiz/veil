"""Synthetic fixture generator: python -m workshop.perf.latency.tests.gen [outdir]."""

from __future__ import annotations

import json
import sys
from pathlib import Path

RECT = [100, 200, 500, 600]


def make(outdir: Path, base: int = 100, step: int = 1, n: int = 120, stem: str = "") -> list[int]:
    """Appearance i at 1000*(i+1) ms with latency base + step*i. Returns the latencies."""
    lats = [base + step * i for i in range(n)]
    feed, dbg = [], []
    for i, lat in enumerate(lats):
        t = 1000 * (i + 1)
        feed.append({"type": "frame", "tMs": t, "visible": [{"itemId": f"cat{i}", "rect": RECT}]})
        if i < 5:  # full stage chain for a few looks
            for k, st in enumerate(("frame", "gate", "ai", "judge", "plan")):
                dbg.append({"kind": "stage", "lookId": i, "stage": st, "tMs": t + 10 * k})
        dbg.append({"kind": "plan", "tMs": t + lat - 10, "lookId": i, "masks": [{"rect": RECT}]})
        dbg.append({"kind": "stage", "lookId": i, "stage": "draw", "tMs": t + lat})
    dbg.sort(key=lambda d: d["tMs"])
    outdir.mkdir(parents=True, exist_ok=True)
    for name, rows in ((f"debug{stem}.jsonl", dbg), (f"feedlog{stem}.jsonl", feed)):
        (outdir / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return lats


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "fixtures"
    make(d)  # p95 = 213
    make(d, base=200, step=3, stem="-slow")  # p95 = 539 -> FAIL
