"""Synthetic screenshots with known truth (harmless shapes, Pillow only).

python -m workshop.screens.synth --out DIR [--n 75] [--near-dupes 2] [--seed 7]

Writes `<app>-feed-NNNN.png` + sidecar, `sources.txt` (`synth`) and `truth.json` (a ScreenLabel
array). Image i: app = APPS[i % 5], class = cats / spiders / clean by (i // 5) % 3, dark when
i % 3 == 0, landscape (780x360) when i % 15 == 0. Stand-ins: cat = orange circle + 2 ears,
spider = black circle + 8 legs, cat-emoji = tiny yellow circle + ears, dog (lookalike, not
labelled) = brown circle + 2 hanging ears.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from workshop.contracts.validate import validate

APPS = ["instagram", "youtube", "chrome", "whatsapp", "x", "reddit"]
CLASSES = ["cats", "spiders", "clean"]
SOURCE = "synth"
SURFACE = "feed"
PORTRAIT = (360, 780)
LANDSCAPE = (780, 360)
MIN_CARD = 130
GAP = 8
MARGIN = 6
EDGE = 3  # gap between a card and the screen edge


def _cat(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, ink: tuple | int) -> None:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink)
    for s in (-1, 1):
        ear = [
            (cx + s * r, cy - r * 0.35),
            (cx + s * r * 0.9, cy - r * 1.5),
            (cx + s * r * 0.2, cy - r * 0.95),
        ]
        d.polygon(ear, fill=ink)


def _spider(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, ink: tuple | int) -> None:
    for s in (-1, 1):
        for k in range(4):
            dy = (k - 1.5) * r * 0.5
            d.line(
                [(cx + s * r * 0.6, cy + dy * 0.6), (cx + s * r * 1.9, cy + dy * 1.8)],
                fill=ink,
                width=3,
            )
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink)


def _dog(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, ink: tuple | int) -> None:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink)
    for s in (-1, 1):
        d.rectangle([cx + s * r - 5, cy - r * 0.6, cx + s * r + 5, cy + r * 0.6], fill=ink)


def _emoji(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, ink: tuple | int) -> None:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink)
    for s in (-1, 1):
        ear = [
            (cx + s * r * 0.95, cy - r * 0.3),
            (cx + s * r * 0.8, cy - r * 1.3),
            (cx + s * r * 0.25, cy - r * 0.9),
        ]
        d.polygon(ear, fill=ink)


# kind -> (draw function, colour, radius range); the emoji circle is 16-24 px across
SHAPES = {
    "cat": (_cat, (240, 140, 40), (26, 38)),
    "spider": (_spider, (12, 12, 12), (14, 20)),
    "dog": (_dog, (200, 150, 100), (24, 34)),
    "emoji": (_emoji, (250, 210, 40), (8, 12)),
}


def _layout(
    rng: random.Random, size: tuple[int, int], n_cards: int
) -> list[tuple[int, int, int, int]]:
    """Cards (x, y, w, h) filling the screen: stacked down a portrait, side by side in landscape."""
    width, height = size
    along = height if height > width else width
    cross = width if height > width else height
    free = along - 2 * EDGE - GAP * (n_cards - 1) - MIN_CARD * n_cards
    cuts = sorted(rng.uniform(0, free) for _ in range(n_cards - 1))
    extra = [b - a for a, b in zip([0.0, *cuts], [*cuts, free], strict=True)]
    cards, pos = [], EDGE
    for e in extra:
        length = int(MIN_CARD + e)
        if height > width:
            cards.append((EDGE, pos, cross - 2 * EDGE, length))
        else:
            cards.append((pos, EDGE, length, cross - 2 * EDGE))
        pos += length + GAP
    return cards


def _place(rng: random.Random, kind: str, card: tuple[int, int, int, int]) -> tuple:
    """Pick a radius and a spot inside the card: (draw fn, colour, cx, cy, r, tight bbox)."""
    fn, color, (lo, hi) = SHAPES[kind]
    r = rng.randint(lo, hi)
    probe = Image.new("L", (300, 300), 0)
    fn(ImageDraw.Draw(probe), 150, 150, r, 255)
    bx1, by1, bx2, by2 = probe.getbbox()  # tight bounds of the drawn pixels
    x, y, w, h = card
    nx = rng.randint(x + MARGIN, x + w - MARGIN - (bx2 - bx1))
    ny = rng.randint(y + MARGIN, y + h - MARGIN - (by2 - by1))
    return fn, color, nx + 150 - bx1, ny + 150 - by1, r, (nx, ny, nx + bx2 - bx1, ny + by2 - by1)


def _pattern(image: Image.Image, rng: random.Random) -> Image.Image:
    """Add a seeded brightness pattern, one block per dHash cell (17 x 16 grid).

    Each row is a reflecting random walk of +-16 levels (range 48), so neighbouring cells always
    differ clearly: unrelated images get unrelated dHash bits and a re-shot copy gets no near-ties.
    """
    cols, rows, step, top = 17, 16, 16, 3
    levels = np.zeros((rows, cols), dtype=np.float32)
    for r in range(rows):
        v = rng.randint(0, top)
        for c in range(cols):
            levels[r, c] = v
            v = v + 1 if v == 0 else v - 1 if v == top else v + rng.choice((-1, 1))
    arr = np.asarray(image).astype(np.float32)
    ys = np.arange(arr.shape[0]) * rows // arr.shape[0]
    xs = np.arange(arr.shape[1]) * cols // arr.shape[1]
    arr += (levels[ys][:, xs] * step - top * step / 2)[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _render(rng: random.Random, shapes: list[str], dark: bool, size: tuple[int, int]) -> tuple:
    """Draw one feed screenshot; return it with [(shape kind, bbox, card)] per drawn shape."""
    image = Image.new("RGB", size, (70, 70, 74) if dark else (190, 190, 193))
    draw = ImageDraw.Draw(image)
    cards = _layout(rng, size, max(len(shapes), rng.randint(2, 4)))
    spots = dict(zip(rng.sample(range(len(cards)), len(shapes)), shapes, strict=True))
    placed = []
    for k, (x, y, w, h) in enumerate(cards):
        if k in spots:
            base = 105 if dark else 200
        else:
            base = rng.randint(85, 110) if dark else rng.randint(150, 175)
        draw.rectangle(
            [x, y, x + w - 1, y + h - 1], fill=tuple(base + rng.randint(-6, 6) for _ in range(3))
        )
        if k in spots:
            fn, color, cx, cy, r, box = _place(rng, spots[k], (x, y, w, h))
            fn(draw, cx, cy, r, color)
            placed.append((spots[k], box, (x, y, w, h)))
            continue
        lo, hi = (130, 165) if dark else (95, 125)
        for _ in range(rng.randint(2, 3)):
            mx = rng.randint(x, x + w - 30)
            mw = rng.randint(20, min(w // 2, x + w - mx))
            my = rng.randint(y + 4, y + h // 2)
            mh = min(rng.randint(12, max(13, y + h - 4 - my)), y + h - 5 - my)
            fill = tuple(rng.randint(lo, hi) for _ in range(3))
            draw.rectangle([mx, my, mx + mw - 1, my + mh], fill=fill)
    return _pattern(image, rng), placed


def _clear_previous(out: Path) -> None:
    """Re-running into an old synthetic folder replaces it; other folders with PNGs are refused."""
    if (out / "truth.json").is_file():
        for pattern in ("*.png", "*.json", "sources.txt"):
            for old in out.glob(pattern):
                old.unlink()
    elif any(out.glob("*.png")):
        raise ValueError(
            f"{out} holds PNGs but no truth.json: refusing to write synthetic data there"
        )


def _near_dupe(image: Image.Image, rng: np.random.Generator) -> Image.Image:
    arr = np.asarray(image).astype(np.int16)
    arr = np.pad(arr, ((0, 0), (2, 0), (0, 0)), mode="edge")[:, :-2, :]
    arr = arr + rng.integers(-3, 4, size=arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def generate(out: Path, n: int = 75, near_dupes: int = 2, seed: int = 7) -> list[dict]:
    """Write the synthetic set to `out` and return the ScreenLabel list (also in truth.json)."""
    if n < 1 or not 0 <= near_dupes <= n:
        raise ValueError("need n >= 1 and 0 <= near_dupes <= n")
    out.mkdir(parents=True, exist_ok=True)
    _clear_previous(out)
    rng = random.Random(seed)
    noise = np.random.default_rng(seed)
    base_time = datetime(2026, 10, 2, 10, 0, 0)
    labels: list[dict] = []
    scope_flip = 0
    counts = {c: 0 for c in CLASSES}
    for i in range(n):
        app, cls = APPS[i % 5], CLASSES[(i // 5) % 3]
        j = counts[cls]
        counts[cls] += 1
        dark = i % 3 == 0
        size = LANDSCAPE if i % 15 == 0 else PORTRAIT
        if cls == "cats":
            shapes = ["cat"] * rng.randint(1, 3) + (["emoji"] if j % 5 == 0 else [])
        elif cls == "spiders":
            shapes = ["spider"] * rng.randint(1, 2)
        else:
            shapes = ["dog"] if j % 2 == 0 else []
        image, placed = _render(rng, shapes, dark, size)
        boxes = []
        for kind, (x1, y1, x2, y2), (cx, cy, cw, ch) in placed:
            if kind == "dog":
                continue
            emoji = kind == "emoji"
            box = {
                "rect": {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1},
                "concept": "spiders" if kind == "spider" else "cats",
                "kind": "emoji" if emoji else "photo",
                "scope": "object" if scope_flip % 2 == 0 else "wholeElement",
            }
            if emoji:
                box["tag"] = "cat-emoji"
            if box["scope"] == "wholeElement":
                box["postRect"] = {"x": cx, "y": cy, "w": cw, "h": ch}
            scope_flip += 1
            boxes.append(box)
        stem = f"{app}-{SURFACE}-{i + 1:04d}"
        meta = {
            "app": app,
            "surface": SURFACE,
            "mode": "dark" if dark else "light",
            "orientation": "landscape" if size == LANDSCAPE else "portrait",
            "source": SOURCE,
        }
        label = {
            "contractVersion": "1.0",
            "image": f"{stem}.png",
            "width": size[0],
            "height": size[1],
            "clean": not boxes,
            "boxes": boxes,
            "meta": meta,
            "labeller": SOURCE,
        }
        if "dog" in shapes:
            label["lookalikes"] = ["dog"]
        validate("ScreenLabel", label)
        stamp = (base_time + timedelta(seconds=7 * i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        image.save(out / f"{stem}.png")
        (out / f"{stem}.json").write_text(
            json.dumps({**meta, "capturedAt": stamp}, indent=2) + "\n", encoding="utf-8"
        )
        labels.append(label)
    for label in labels[:near_dupes]:
        stem = label["image"][: -len(".png")]
        with Image.open(out / label["image"]) as base:
            _near_dupe(base.convert("RGB"), noise).save(out / f"{stem}-dup.png")
        side = json.loads((out / f"{stem}.json").read_text(encoding="utf-8"))
        (out / f"{stem}-dup.json").write_text(json.dumps(side, indent=2) + "\n", encoding="utf-8")
        labels.append({**label, "image": f"{stem}-dup.png"})
    (out / "sources.txt").write_text(f"# synthetic set\n{SOURCE}\n", encoding="utf-8")
    (out / "truth.json").write_text(json.dumps(labels, indent=1) + "\n", encoding="utf-8")
    return labels


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="workshop.screens.synth", description="Synthetic set.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n", type=int, default=75)
    parser.add_argument("--near-dupes", type=int, default=2)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    try:
        labels = generate(args.out, args.n, args.near_dupes, args.seed)
    except ValueError as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {len(labels)} screenshots to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
