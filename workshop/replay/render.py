"""Cover renderer: paint a MaskPlan onto a frame."""

from __future__ import annotations

import cv2
import numpy as np


def rect_to_frame(
    rect: dict, frame_w: int, frame_h: int, screen_width: int
) -> tuple[int, int, int, int]:
    """Screen-px rect -> clipped frame-px (x0, y0, x1, y1), uniform scale frame_w/screen_width."""
    x0 = rect["x"] * frame_w // screen_width
    y0 = rect["y"] * frame_w // screen_width
    x1 = (rect["x"] + rect["w"]) * frame_w // screen_width
    y1 = (rect["y"] + rect["h"]) * frame_w // screen_width
    return max(x0, 0), max(y0, 0), min(x1, frame_w), min(y1, frame_h)


def paint(
    frame_bgr: np.ndarray, plan: dict, screen_width: int, solid_bgr=(40, 40, 40)
) -> np.ndarray:
    out = frame_bgr.copy()
    h, w = out.shape[:2]
    for mask in plan.get("masks", []):
        x0, y0, x1, y1 = rect_to_frame(mask["rect"], w, h, screen_width)
        if x1 <= x0 or y1 <= y0:
            continue
        style = mask.get("style", "solid")
        region = out[y0:y1, x0:x1]
        if style == "blur":
            out[y0:y1, x0:x1] = cv2.GaussianBlur(region, (0, 0), 8)
        elif style == "mosaic":
            small = cv2.resize(region, (max(1, (x1 - x0) // 12), max(1, (y1 - y0) // 12)))
            out[y0:y1, x0:x1] = cv2.resize(
                small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST
            )
        else:
            out[y0:y1, x0:x1] = solid_bgr
    return out
