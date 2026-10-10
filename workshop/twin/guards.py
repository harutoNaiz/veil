"""Piece guards applied after the Judge (twin of com.veil.brain.judge.Guards).

Pure functions on plain data so Kotlin can mirror them exactly. Every constant is global.

flat       a piece whose grey-level standard deviation is below FLAT_STD (0..255 scale) shows no
           content (blank, loading or solid-colour area); it can never be a hide.
container  a tile, crop or whole-screen piece is a hide only if the tight evidence agrees. A finder
           box is "related" to a container when their overlap is >= RELATED of the smaller area.
           mode "agree": when related boxes exist, at least one must hide too.
           mode "wins":  when related boxes exist the container never hides; the boxes decide
                         (tight masks). Containers with no related box stay the fallback.
"""

from __future__ import annotations

FLAT_STD = 6.0
RELATED = 0.5
CONTAINERS = ("tile", "crop", "whole")


def _inter(a: dict, b: dict) -> int:
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return max(0, w) * max(0, h)


def apply(
    regions: list[dict],
    hide: list[bool],
    flat: list[bool] | None = None,
    container: str | None = "agree",
) -> list[bool]:
    out = list(hide)
    if flat is not None:
        out = [h and not f for h, f in zip(out, flat, strict=True)]
    if container:
        finders = [i for i, r in enumerate(regions) if r["source"] == "finder"]
        base = list(out)
        for k, r in enumerate(regions):
            if not base[k] or r["source"] not in CONTAINERS:
                continue
            ra = r["rect"]["w"] * r["rect"]["h"]
            rel = [
                j
                for j in finders
                if _inter(r["rect"], regions[j]["rect"])
                >= RELATED * min(ra, regions[j]["rect"]["w"] * regions[j]["rect"]["h"])
            ]
            if rel and (container == "wins" or not any(base[j] for j in rel)):
                out[k] = False
    return out


# ---- tighten (twin of RegionLane.tighten): tight hides win, coarse hides stay only as the fallback
# ----
FINE_MAX_SCREEN = 0.35  # layout nodes up to this share of the screen count as fine
COARSER = 1.5  # a hide this many times larger than a fine hide it overlaps gives way
OVERLAP_FINE = 0.1  # ... when it holds at least this share of the fine hide's area
FLAT_GRID = (
    32  # flat is measured on a FLAT_GRID x FLAT_GRID luma sample grid (what the phone can afford)
)


def sample_luma(img, rect: dict, n: int = FLAT_GRID) -> list[int]:
    """n x n luma samples at the cell centres of rect (screen px), ints (r*299+g*587+b*114)//1000.
    Same sampling as Hashes.lumaGrid on the phone."""
    import numpy as np

    a = np.asarray(img.convert("RGB"), dtype=np.int64)
    h, w = a.shape[:2]
    out = []
    for r in range(n):
        y = min(max(int((rect["y"] + rect["h"] * (r + 0.5) / n) / h * h), 0), h - 1)
        for c in range(n):
            x = min(max(int((rect["x"] + rect["w"] * (c + 0.5) / n) / w * w), 0), w - 1)
            p = a[y, x]
            out.append(int((p[0] * 299 + p[1] * 587 + p[2] * 114) // 1000))
    return out


def is_flat(luma: list[int]) -> bool:
    if not luma:
        return True
    m = sum(luma) / len(luma)
    return (sum((v - m) ** 2 for v in luma) / len(luma)) ** 0.5 < FLAT_STD


# a fine hide is a partial view of the object: coarse hides are clipped to it grown by this share
# per side
GROW = 0.15


def tighten(
    regions: list[dict], hide: list[bool], screen_area: int, grow: float = GROW
) -> list[dict]:
    """Rects to cover (dicts x,y,w,h). Fine hides = finder boxes (and layout nodes <= 35 % of
    the screen). A non-finder hide that is >= 1.5x larger than a fine hide it overlaps by
    >= 10 % of that fine hide's area is not covered whole: it is clipped to each such fine hide
    grown by `grow` per side (the detector often boxes only part of the object); a clip that is
    empty vanishes. Every other hide keeps its rect."""

    def area(r: dict) -> int:
        return r["rect"]["w"] * r["rect"]["h"]

    fine = [
        i
        for i, r in enumerate(regions)
        if hide[i]
        and (
            r["source"] == "finder"
            or (r["source"] == "layout" and area(r) <= FINE_MAX_SCREEN * screen_area)
        )
    ]
    out = []
    for k, r in enumerate(regions):
        if not hide[k]:
            continue
        under = [
            q
            for q in fine
            if q != k
            and r["source"] != "finder"
            and area(r) * 2 >= area(regions[q]) * 3
            and _inter(r["rect"], regions[q]["rect"]) * 10 >= area(regions[q])
        ]
        if not under:
            if fine and k not in fine:
                continue  # individual regions only: a coarse hide on no tight box is dropped
            out.append(dict(r["rect"]))
            continue
        for q in under:
            out.append(clip_to_grown(r["rect"], regions[q]["rect"], grow))
    return [o for o in out if o["w"] > 0 and o["h"] > 0]


def clip_to_grown(r: dict, f: dict, grow: float) -> dict:
    """r intersected with f grown by `grow` of its width/height per side (integer px, rounded
    half to even)."""
    gx, gy = round(f["w"] * grow), round(f["h"] * grow)
    x0, y0 = max(r["x"], f["x"] - gx), max(r["y"], f["y"] - gy)
    x1, y1 = min(r["x"] + r["w"], f["x"] + f["w"] + gx), min(r["y"] + r["h"], f["y"] + f["h"] + gy)
    return {"x": x0, "y": y0, "w": max(0, x1 - x0), "h": max(0, y1 - y0)}
