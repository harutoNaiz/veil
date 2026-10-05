"""Drift of the glued box against ground truth (feed log) or tracked frame patches."""

import argparse
import bisect
import json
from pathlib import Path

import numpy as np


def _rows(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in lines if x.strip()]


def drift_stats(feed: Path, glue: Path) -> tuple[float, float]:
    """Feed rows: {tMs, itemY} (item under the start point). Glue rows: {tMs, y}."""
    g = sorted(_rows(glue), key=lambda r: r["tMs"])
    f = [r for r in _rows(feed) if "itemY" in r]
    if not g or not f:
        return 0.0, 0.0
    ts = [r["tMs"] for r in g]
    base = f[0]["itemY"] - g[0]["y"]
    diffs = []
    for r in f:
        i = bisect.bisect_left(ts, r["tMs"])
        cand = range(max(i - 1, 0), min(i + 1, len(g) - 1) + 1)
        k = min(cand, key=lambda j: abs(ts[j] - r["tMs"]))
        diffs.append(abs(g[k]["y"] - (r["itemY"] - base)))
    a = np.array(diffs, dtype=float)
    return float(a.max()), float(np.percentile(a, 95))


def track_patch(prev: np.ndarray, cur: np.ndarray, x: int, y: int, size: int = 64, rng: int = 48):
    """Vertical shift of the patch at (x, y) from prev to cur via SAD search."""
    patch = prev[y : y + size, x : x + size].astype(np.int32)
    best, best_dy = None, 0
    for dy in range(-rng, rng + 1):
        yy = y + dy
        if yy < 0 or yy + size > cur.shape[0]:
            continue
        sad = int(np.abs(cur[yy : yy + size, x : x + size].astype(np.int32) - patch).sum())
        if best is None or sad < best:
            best, best_dy = sad, dy
    return best_dy


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--testfeed", nargs=2, metavar=("FEEDLOG", "GLUE"))
    ap.add_argument("--frames", nargs=2, metavar=("DIR", "GLUE"))
    a = ap.parse_args()
    if a.testfeed:
        mx, p95 = drift_stats(Path(a.testfeed[0]), Path(a.testfeed[1]))
        print(f"drift max={mx:.1f}px p95={p95:.1f}px")
        return 0 if mx <= 8 else 1
    if a.frames:
        from PIL import Image

        files = sorted(Path(a.frames[0]).glob("*.png"))
        glue = _rows(Path(a.frames[1]))
        imgs = [np.asarray(Image.open(p).convert("L")) for p in files]
        shifts = [track_patch(imgs[i], imgs[i + 1], 8, 8) for i in range(len(imgs) - 1)]
        print(f"frames={len(imgs)} glue_samples={len(glue)} patch_shift_sum={sum(shifts)}")
        return 0
    ap.error("need --testfeed or --frames")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
