"""2.2.1 Change detector: integer-only tile change with scroll compensation and scene cuts."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

THUMB_W, THUMB_H, TILE = 32, 64, 8
_COLS = THUMB_W // TILE
_ROWS = THUMB_H // TILE


@dataclass(frozen=True)
class ChangeParams:
    ignore_top_rows: int = 2
    ignore_bottom_rows: int = 2
    tile_level: int = 12
    cut_tile_level: int = 40
    cut_pct: int = 60
    cut_global: int = 30
    cut_min_tiles: int = 8


@dataclass(frozen=True)
class ChangeResult:
    tile_scores: tuple[int, ...]
    changed_tiles: int
    scene_cut: bool
    score: int
    revealed_rows: tuple[int, int] | None
    changed_box: tuple[int, int, int, int] | None
    shift_rows: int


DEFAULT_PARAMS = ChangeParams()


def thumb(frame_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (THUMB_W, THUMB_H), interpolation=cv2.INTER_AREA)


def shift_rows(dy_screen: int, width: int, height: int, screen_width: int) -> int:
    num = dy_screen * width * THUMB_H
    den = screen_width * height
    mag = (2 * abs(num) + den) // (2 * den)
    return -mag if num < 0 else mag


def detect(
    cur: np.ndarray, ref: np.ndarray | None, dy_rows: int, p: ChangeParams = DEFAULT_PARAMS
) -> ChangeResult:
    if ref is None:
        box = (0, 0, THUMB_W, THUMB_H)
        return ChangeResult((255,) * (_ROWS * _COLS), _ROWS * _COLS, False, 0, None, box, 0)
    top, bot = p.ignore_top_rows, THUMB_H - p.ignore_bottom_rows
    # revealed band rows: those whose shifted source falls outside the band
    if dy_rows >= bot - top or -dy_rows >= bot - top:
        rev = (top, bot)
    elif dy_rows > 0:
        rev = (top, top + dy_rows)
    elif dy_rows < 0:
        rev = (bot + dy_rows, bot)
    else:
        rev = None
    c = cur.astype(np.int32)
    r = ref.astype(np.int32)
    diff = np.zeros((THUMB_H, THUMB_W), dtype=np.int32)
    lo, hi = max(top, top + dy_rows), min(bot, bot + dy_rows)
    if hi > lo:
        diff[lo:hi] = np.abs(c[lo:hi] - r[lo - dy_rows : hi - dy_rows])
    scores = []
    compared = large = 0
    tot_sum = tot_n = 0
    for tr in range(_ROWS):
        y0, y1 = max(tr * TILE, top), min(tr * TILE + TILE, bot)
        for tc in range(_COLS):
            n = (y1 - y0) * TILE if y1 > y0 else 0
            if n == 0:
                scores.append(0)
                continue
            if rev is not None and y0 < rev[1] and y1 > rev[0]:
                scores.append(255)
                continue
            s = int(diff[y0:y1, tc * TILE : tc * TILE + TILE].sum())
            sc = s // n
            scores.append(sc)
            compared += 1
            tot_sum += s
            tot_n += n
            if sc >= p.cut_tile_level:
                large += 1
    score = tot_sum // tot_n if tot_n else 0
    changed = [i for i, s in enumerate(scores) if s >= p.tile_level]
    box = None
    if changed:
        rows = [i // _COLS for i in changed]
        cols = [i % _COLS for i in changed]
        box = (min(cols) * TILE, min(rows) * TILE, (max(cols) + 1) * TILE, (max(rows) + 1) * TILE)
    cut = (
        compared >= p.cut_min_tiles
        and large * 100 >= p.cut_pct * compared
        and score >= p.cut_global
    )
    return ChangeResult(tuple(scores), len(changed), bool(cut), score, rev, box, int(dy_rows))


def thumb_box_to_screen(box: tuple[int, int, int, int], frame: dict) -> dict:
    sw, w, h = frame["screenWidth"], frame["width"], frame["height"]
    sh = h * sw // w
    x0, y0, x1, y1 = box
    sx0, sx1 = x0 * sw // THUMB_W, x1 * sw // THUMB_W
    sy0, sy1 = y0 * h * sw // (THUMB_H * w), y1 * h * sw // (THUMB_H * w)
    sx0, sx1 = min(sx0, sw), min(sx1, sw)
    sy0, sy1 = min(sy0, sh), min(sy1, sh)
    return {"x": sx0, "y": sy0, "w": sx1 - sx0, "h": sy1 - sy0}
