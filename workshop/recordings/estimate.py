"""Estimate scroll from frame differences (row-profile shift search); events are estimated."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

MAX_SHIFT = 150
MIN_OVERLAP = 300


def _best_shift(prev: np.ndarray, cur: np.ndarray) -> int:
    """Shift s (frame px) with cur[y] ~= prev[y - s]; 0 when nothing matches well."""
    h = len(cur)
    errs = {}
    for s in range(-MAX_SHIFT, MAX_SHIFT + 1):
        if h - abs(s) < MIN_OVERLAP:
            continue
        a, b = (cur[s:], prev[: h - s]) if s >= 0 else (cur[: h + s], prev[-s:])
        errs[s] = float(np.abs(a - b).mean())
    e0 = errs[0]
    s = min(errs, key=lambda k: (errs[k], abs(k)))
    if s == 0 or errs[s] > 3.0 or errs[s] > 0.4 * e0:
        return 0
    return s


def estimate_scroll(
    video: Path,
    screen_width: int,
    package: str,
    *,
    fps: float = 30.0,
    t0_ms: int = 0,
    start_id: int = 0,
) -> list[dict]:
    cap = cv2.VideoCapture(str(video))
    events: list[dict] = []
    prev = None
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        prof = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32).mean(axis=1)
        if prev is not None:
            s = _best_shift(prev, prof)
            if s != 0:
                scale = screen_width / frame.shape[1]
                events.append(
                    {
                        "contractVersion": "1.0",
                        "eventId": start_id + len(events),
                        "tMs": t0_ms + int(i * 1000 // fps),
                        "type": "scrolled",
                        "packageName": package,
                        "dx": 0,
                        "dy": int(round(s * scale)),
                        "estimated": True,
                    }
                )
        prev = prof
        i += 1
    cap.release()
    return events
