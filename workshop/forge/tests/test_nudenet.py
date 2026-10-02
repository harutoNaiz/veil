import numpy as np

from workshop.forge.nudenet.decode import agreement, decode, letterbox_params
from workshop.forge.nudenet.parity import agreement_pooled


def _raw(rows, ncls=3):
    """rows: (cx, cy, w, h, cls, score) -> (1, 4+C, N)."""
    a = np.zeros((len(rows), 4 + ncls), dtype=np.float32)
    for i, (cx, cy, w, h, c, s) in enumerate(rows):
        a[i, :4] = (cx, cy, w, h)
        a[i, 4 + c] = s
    return a.T[None]


def test_threshold():
    raw = _raw([(50, 50, 20, 20, 0, 0.9), (150, 150, 20, 20, 1, 0.1)])
    out = decode(raw, conf=0.2)
    assert len(out) == 1 and out[0][0] == 0 and out[0][2] == (40, 40, 60, 60)


def test_nms_same_class_only():
    raw = _raw([(50, 50, 20, 20, 0, 0.9), (51, 50, 20, 20, 0, 0.8), (50, 50, 20, 20, 1, 0.7)])
    out = decode(raw, iou=0.45)
    assert [(c, round(s, 1)) for c, s, _ in out] == [(0, 0.9), (1, 0.7)]


def test_unletterbox():
    lb = letterbox_params(640, 320, 320)  # scale 0.5, no offset
    assert lb == (0.5, 0.0, 0.0)
    out = decode(_raw([(50, 50, 20, 20, 0, 0.9)]), letterbox=lb)
    assert out[0][2] == (80, 80, 120, 120)
    out = decode(_raw([(50, 60, 20, 20, 0, 0.9)]), letterbox=(1.0, 10.0, 20.0))
    assert out[0][2] == (30, 30, 50, 50)


def test_agreement_metric():
    a = (0, 0.9, (0, 0, 10, 10))
    assert agreement([], []) == (1, 1)
    assert agreement([a], [a]) == (1, 1)
    assert agreement([a], [(1, 0.9, (0, 0, 10, 10))]) == (0, 1)
    assert agreement([a], [a, (0, 0.5, (50, 50, 60, 60))]) == (1, 2)
    assert agreement_pooled([([a], [a]), ([a], [])]) == 0.5
