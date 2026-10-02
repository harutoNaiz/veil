import random
from pathlib import Path

import cv2
import numpy as np

from workshop.recordings.synth_session import _canvas
from workshop.twin.cache import FingerprintCache, _sig_ok, hamming, phash64, signature, usable


def _sources():
    """(label, image) pairs: public photos, synthetic feed canvases."""
    out = []
    for f in sorted(Path("data/public/photos").rglob("*.jpg")):
        im = cv2.imread(str(f))
        if im is not None:
            out.append(("photo", im))
    for seed in range(1, 40):
        out.append(("synth", _canvas("feed", 6400, seed)[0]))
    return out


def _crops(n=1000):
    """n genuinely different crops: varied positions/scales, near-duplicates skipped."""
    srcs = _sources()
    rng = random.Random(7)
    chosen, sigs = [], []
    tries = 0
    while len(chosen) < n and tries < 60000:
        tries += 1
        kind, im = srcs[rng.randrange(len(srcs))]
        ih, iw = im.shape[:2]
        side = rng.choice([64, 96, 128, 160, 200]) if kind == "photo" else 128
        if side + 8 > min(ih, iw):
            continue
        x = rng.randrange(4, iw - side - 4)
        y = rng.randrange(4, ih - side - 4)
        c = im[y : y + side, x : x + side]
        if not usable(c):
            continue
        sg = signature(c)
        if any(_sig_ok(sg, o) for o in sigs):
            continue
        chosen.append((kind, im, x, y, side))
        sigs.append(sg)
    return chosen


def _noisy(c, rng):
    noise = rng.integers(-3, 4, c.shape)
    return np.clip(c.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def test_wrong_reuse_and_hit_rate():
    items = _crops()
    assert len(items) == 1000
    rng = np.random.default_rng(1)
    cache = FingerprintCache(capacity=5000)
    for i, (_, im, x, y, s) in enumerate(items):
        c = im[y : y + s, x : x + s]
        cache.put(phash64(c), np.array([i], dtype=np.float32), 0, signature(c))
    wrong = near_hits = 0
    per = {"photo": [0, 0], "synth": [0, 0]}
    for i, (kind, im, x, y, s) in enumerate(items):
        exact = im[y : y + s, x : x + s]
        near = _noisy(im[y : y + s, x + 2 : x + 2 + s], rng)
        for k, c in enumerate((exact, near)):
            r = cache.get(phash64(c), 0, signature(c))
            if r is not None:
                wrong += int(int(r[0]) != i)
                if k:
                    near_hits += 1
                    per[kind][0] += 1
            if k:
                per[kind][1] += 1
    print(
        f"CACHE near-dup hit {near_hits * 100 // 1000}% wrong {wrong}/2000 "
        f"(photo {per['photo'][0]}/{per['photo'][1]}, synth {per['synth'][0]}/{per['synth'][1]})"
    )
    assert wrong < 2
    assert near_hits >= 800


def test_lru_ttl_clear():
    c = FingerprintCache(capacity=10, max_dist=0, ttl_ms=100)
    for i in range(12):
        c.put(1 << i, np.zeros(2), 0)
    assert len(c) == 10 and c.get(1, 0) is None and c.get(1 << 11, 0) is not None
    assert c.get(1 << 11, 101) is None
    c.clear()
    assert len(c) == 0
    assert hamming(0b1011, 0b0001) == 2


def test_fingerprints_not_verdicts():
    c = FingerprintCache()
    c.put(5, np.array([1, 0], dtype=np.float16), 0)
    got = c.get(5, 0)
    assert got.dtype == np.float16

    def verdict(concept):
        return float(got.astype(np.float32) @ concept) >= 0.5

    assert verdict(np.array([1.0, 0.0])) is True
    assert verdict(np.array([0.0, 1.0])) is False
