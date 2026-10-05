"""Do our own covers appear in our own capture? Checks PNG pixels inside reported rects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

COVER_RGB = (0x20, 0x21, 0x24)


def scaled(rect: dict, sx: float, sy: float) -> tuple[int, int, int, int]:
    """Round outward to capture scale: (x0, y0, x1, y1)."""
    x0 = int(np.floor(rect["x"] * sx))
    y0 = int(np.floor(rect["y"] * sy))
    x1 = int(np.ceil((rect["x"] + rect["w"]) * sx))
    y1 = int(np.ceil((rect["y"] + rect["h"]) * sy))
    return x0, y0, x1, y1


def cover_fraction(img: np.ndarray, box: tuple[int, int, int, int], tol: int = 12) -> float:
    x0, y0, x1, y1 = box
    crop = img[max(y0, 0) : y1, max(x0, 0) : x1, :3].astype(int)
    if crop.size == 0:
        return 0.0
    close = np.abs(crop - np.array(COVER_RGB)).max(axis=2) <= tol
    return float(close.mean())


def edge_error(img: np.ndarray, box: tuple[int, int, int, int], tol: int = 12) -> int:
    """Max px between the reported left/top edge and the first cover-coloured column/row."""
    x0, y0, x1, y1 = box
    mid_y, mid_x = (y0 + y1) // 2, (x0 + x1) // 2
    row = np.abs(img[mid_y, :, :3].astype(int) - np.array(COVER_RGB)).max(axis=1) <= tol
    col = np.abs(img[:, mid_x, :3].astype(int) - np.array(COVER_RGB)).max(axis=1) <= tol
    xs, ys = np.flatnonzero(row), np.flatnonzero(col)
    if len(xs) == 0 or len(ys) == 0:
        return 999
    return int(max(abs(xs[0] - x0), abs(ys[0] - y0)))


def check(frames: list[dict], image_dir: Path) -> dict:
    results = []
    for f in frames:
        if not f.get("ownOverlay") or "image" not in f:
            continue
        path = image_dir / f["image"]
        if not path.exists():
            continue
        img = np.array(Image.open(path).convert("RGB"))
        sx, sy = img.shape[1] / f["screenWidth"], img.shape[0] / f["screenHeight"]
        for r in f["ownOverlay"]:
            box = scaled(r, sx, sy)
            results.append(
                {
                    "image": f["image"],
                    "fraction": cover_fraction(img, box),
                    "edgeErrPx": edge_error(img, box),
                }
            )
    captured = bool(results) and sum(x["fraction"] >= 0.9 for x in results) > len(results) / 2
    aligned = bool(results) and all(x["edgeErrPx"] <= 2 for x in results if x["fraction"] >= 0.9)
    return {"coversCaptured": captured, "aligned2px": aligned, "samples": results}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("frames_own", type=Path, help="frames_own.jsonl from own_join")
    p.add_argument("image_dir", type=Path)
    a = p.parse_args(argv)
    lines = a.frames_own.read_text(encoding="utf-8").splitlines()
    res = check([json.loads(x) for x in lines if x.strip()], a.image_dir)
    print(f"covers captured: {'yes' if res['coversCaptured'] else 'no'}")
    print(f"edge alignment <= 2 px: {'yes' if res['aligned2px'] else 'no'}")
    print(json.dumps(res["samples"][:4]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
