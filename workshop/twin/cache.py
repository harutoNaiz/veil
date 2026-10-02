"""Guard-style picture-hash fingerprint cache (2.3.2). Stores fingerprints, never verdicts."""

from __future__ import annotations

from collections import OrderedDict

import cv2
import numpy as np


def _gray(crop_bgr: np.ndarray) -> np.ndarray:
    if crop_bgr.ndim == 3:
        return cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    return crop_bgr


def phash64(crop_bgr: np.ndarray) -> int:
    g = cv2.resize(_gray(crop_bgr), (32, 32), interpolation=cv2.INTER_AREA)
    d = cv2.dct(g.astype(np.float32))[:8, :8].flatten()
    med = np.median(d)
    h = 0
    for b in (d > med).tolist():
        h = (h << 1) | int(b)
    return h


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def usable(crop_bgr: np.ndarray) -> bool:
    return float(_gray(crop_bgr).std()) >= 8


SIG_MAD_MAX = 10


def signature(crop_bgr: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Tiny colour signature: 8x8 BGR uint8 thumbnail plus the crop size."""
    h, w = crop_bgr.shape[:2]
    return cv2.resize(crop_bgr, (8, 8), interpolation=cv2.INTER_AREA), w, h


def _sig_ok(a: tuple, b: tuple) -> bool:
    (ta, wa, ha), (tb, wb, hb) = a, b
    if abs(wa - wb) * 10 > wa or abs(ha - hb) * 10 > ha:
        return False
    mad = int(np.abs(ta.astype(np.int16) - tb.astype(np.int16)).sum()) // ta.size
    return mad <= SIG_MAD_MAX


class FingerprintCache:
    def __init__(self, capacity: int = 8000, max_dist: int = 10, ttl_ms: int = 60000):
        self.capacity = capacity
        self.max_dist = max_dist
        self.ttl_ms = ttl_ms
        self._e: OrderedDict[int, tuple] = OrderedDict()
        self._n = 0
        self.hits = 0
        self.misses = 0

    def __len__(self) -> int:
        return len(self._e)

    def get(self, h: int, t_ms: int, sig: tuple | None = None) -> np.ndarray | None:
        best = None
        for eid, (_, t, esig, eh) in self._e.items():
            if t_ms - t > self.ttl_ms:
                continue
            d = hamming(h, eh)
            if d > self.max_dist:
                continue
            if sig is not None and esig is not None and not _sig_ok(sig, esig):
                continue
            if best is None or (d, -t) < (best[0], -best[1]):
                best = (d, t, eid)
        if best is None:
            self.misses += 1
            return None
        self.hits += 1
        self._e.move_to_end(best[2])
        return self._e[best[2]][0]

    def put(self, h: int, fingerprint: np.ndarray, t_ms: int, sig: tuple | None = None) -> None:
        self._n += 1
        self._e[self._n] = (np.asarray(fingerprint, dtype=np.float16), t_ms, sig, h)
        while len(self._e) > self.capacity:
            self._e.popitem(last=False)

    def clear(self) -> None:
        self._e.clear()
