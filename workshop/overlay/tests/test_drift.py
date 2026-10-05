import json
from pathlib import Path

import numpy as np

from workshop.overlay.drift import drift_stats, track_patch


def _w(p: Path, rows: list[dict]) -> Path:
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


def _glue() -> list[dict]:
    return [{"tMs": 100 * i, "y": 1000 - 10 * i, "eventDy": -10} for i in range(1, 6)]


def _feed() -> list[dict]:
    return [{"tMs": 100 * i, "itemY": 1000 - 10 * i} for i in range(1, 6)]


def test_zero_drift(tmp_path):
    mx, p95 = drift_stats(_w(tmp_path / "f", _feed()), _w(tmp_path / "g", _glue()))
    assert mx == 0 and p95 == 0


def test_known_drift(tmp_path):
    g = _glue()
    g[-1]["y"] += 12
    mx, _ = drift_stats(_w(tmp_path / "f", _feed()), _w(tmp_path / "g", g))
    assert mx == 12


def test_sad_tracker():
    rng = np.random.default_rng(1)
    img = rng.integers(0, 255, (400, 200), dtype=np.uint8)
    cur = np.roll(img, 17, axis=0)
    assert track_patch(img, cur, 8, 100) == 17
