"""Pieces: cut a screenshot into Region dicts (contract v1.0): whole screen, tiles and crops.

Variant A has no layout lane yet (DV-6), so pieces are the whole image, an overlapping grid of tiles
and three square crops along the long side (top, middle, bottom of a portrait screen).
"""

from __future__ import annotations

from PIL import Image


def _rect(x: float, y: float, w: float, h: float, width: int, height: int) -> dict:
    x0, y0 = max(0, round(x)), max(0, round(y))
    x1, y1 = min(width, round(x + w)), min(height, round(y + h))
    return {"x": x0, "y": y0, "w": max(1, x1 - x0), "h": max(1, y1 - y0)}


def _region(rid: str, rect: dict, look_id: int, source: str, kind: str, parent: str | None) -> dict:
    region = {
        "contractVersion": "1.0",
        "regionId": rid,
        "lookId": look_id,
        "tMs": 0,
        "rect": rect,
        "source": source,
        "kind": kind,
    }
    if parent:
        region["parentRegionId"] = parent
    return region


def make_pieces(
    img: Image.Image,
    look_id: int = 0,
    grid: tuple[int, int] = (3, 6),
    overlap: float = 0.25,
    tall_crops: int = 3,
    finder_boxes: list[dict] | None = None,
    tiles: bool = True,
) -> list[dict]:
    """Region dicts: "whole" + "t{r}-{c}" tiles + "c{i}" crops + the finder boxes as given.

    `grid` is (columns, rows) for a portrait screen; a landscape screen swaps it so both give the
    same tile count. Tiles overlap by `overlap` of their own size. Crops are `tall_crops` squares
    of side min(W, H) spread along the long side.
    """
    width, height = img.size
    pieces = [
        _region(
            "whole", _rect(0, 0, width, height, width, height), look_id, "whole", "screen", None
        )
    ]
    if tiles:
        cols, rows = grid if height >= width else (grid[1], grid[0])
        step_w, step_h = 1 + (cols - 1) * (1 - overlap), 1 + (rows - 1) * (1 - overlap)
        tw, th = width / step_w, height / step_h
        for r in range(rows):
            for c in range(cols):
                x = c * tw * (1 - overlap)
                y = r * th * (1 - overlap)
                rect = _rect(x, y, tw, th, width, height)
                pieces.append(_region(f"t{r}-{c}", rect, look_id, "tile", "unknown", "whole"))
    side = min(width, height)
    for i in range(tall_crops):
        frac = i / (tall_crops - 1) if tall_crops > 1 else 0.5
        if height >= width:
            rect = _rect(0, frac * (height - side), side, side, width, height)
        else:
            rect = _rect(frac * (width - side), 0, side, side, width, height)
        pieces.append(_region(f"c{i}", rect, look_id, "crop", "unknown", "whole"))
    pieces.extend(dict(box) for box in (finder_boxes or []))
    return pieces


def crop(img: Image.Image, rect: dict) -> Image.Image:
    return img.crop((rect["x"], rect["y"], rect["x"] + rect["w"], rect["y"] + rect["h"]))
