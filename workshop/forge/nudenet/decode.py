"""NudeNet (YOLOv8) output decoding, numpy only. Reference for the Kotlin port."""

from __future__ import annotations

import numpy as np

# letterbox = (scale, pad_x, pad_y): input_xy = orig_xy * scale + pad
Letterbox = tuple[float, float, float]


def letterbox_params(width: int, height: int, size: int) -> Letterbox:
    """NudeNet-style square pad (bottom/right) then resize: scale = size / max(w, h), no offset."""
    return (size / max(width, height), 0.0, 0.0)


def _iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    x1 = np.maximum(a[0], b[:, 0])
    y1 = np.maximum(a[1], b[:, 1])
    x2 = np.minimum(a[2], b[:, 2])
    y2 = np.minimum(a[3], b[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    aa = (a[2] - a[0]) * (a[3] - a[1])
    ab = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(aa + ab - inter, 1e-9)


def nms(boxes: np.ndarray, scores: np.ndarray, iou: float) -> list[int]:
    order = [int(i) for i in np.argsort(-scores, kind="stable")]
    keep: list[int] = []
    while order:
        i = order.pop(0)
        keep.append(i)
        if order:
            ious = _iou(boxes[i], boxes[order])
            order = [j for j, v in zip(order, ious, strict=True) if v <= iou]
    return keep


def decode(
    raw: np.ndarray,
    conf: float = 0.2,
    iou: float = 0.45,
    letterbox: Letterbox = (1.0, 0.0, 0.0),
) -> list[tuple[int, float, tuple[float, float, float, float]]]:
    """raw (1, 4+C, N) or (4+C, N): cx,cy,w,h in input pixels then class scores.

    Returns [(cls, score, (x1, y1, x2, y2) in original pixels)], class-wise NMS."""
    p = np.asarray(raw, dtype=np.float32)
    if p.ndim == 3:
        p = p[0]
    p = p.T  # (N, 4+C)
    cls_scores = p[:, 4:]
    cls = cls_scores.argmax(axis=1)
    score = cls_scores.max(axis=1)
    m = score >= conf
    p, cls, score = p[m], cls[m], score[m]
    if len(score) == 0:
        return []
    cx, cy, w, h = p[:, 0], p[:, 1], p[:, 2], p[:, 3]
    xyxy = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)
    scale, px, py = letterbox
    xyxy = (xyxy - np.array([px, py, px, py], dtype=np.float32)) / scale
    out = []
    for c in np.unique(cls):
        idx = np.where(cls == c)[0]
        for k in nms(xyxy[idx], score[idx], iou):
            j = idx[k]
            out.append((int(c), float(score[j]), tuple(float(v) for v in xyxy[j])))
    out.sort(key=lambda d: -d[1])
    return out


def agreement(ref: list, new: list, iou_min: float = 0.5) -> tuple[int, int]:
    """(matched, max(#ref, #new)) for one image; both empty -> (1, 1) (counts as agreement)."""
    if not ref and not new:
        return 1, 1
    used: set[int] = set()
    matched = 0
    for c, _s, box in ref:
        best, bi = 0.0, -1
        for i, (c2, _s2, box2) in enumerate(new):
            if i in used or c2 != c:
                continue
            v = float(_iou(np.array(box), np.array([box2]))[0])
            if v > best:
                best, bi = v, i
        if bi >= 0 and best >= iou_min:
            used.add(bi)
            matched += 1
    return matched, max(len(ref), len(new))
