"""OnnxFinder: runs the exported YOLOE finder with onnxruntime-cpu (SPEC 3.1.2 section 2).

Mirrors `workshop.twin.finder.Finder` for boxes(), but with a fixed 640x640 square letterbox.
Decoding after the graph (threshold, un-letterbox, min side, NMS) is numpy only: it is the
reference for the Kotlin port.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from workshop.forge.common import FORGE_DATA, FORGE_SRC
from workshop.twin.finder import CONF, IOU, MAX_BOXES, MIN_SIDE, PROPOSAL_VOCAB, Finder

IMGSZ = 640
PAD_VALUE = 114
FINDER_FILE = "yoloe-26s-embed-top100.onnx"
TEXT_FILE = "mobileclip2-b-text.onnx"
PROPOSAL_PE = FORGE_SRC / "yoloe" / "proposal_pe.npy"


def _l2(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def letterbox_params(w0: int, h0: int) -> tuple[float, int, int]:
    """(gain, pad_left, pad_top) of the square centred letterbox (Ultralytics rounding)."""
    gain = min(IMGSZ / h0, IMGSZ / w0)
    dw, dh = (IMGSZ - round(w0 * gain)) / 2, (IMGSZ - round(h0 * gain)) / 2
    return gain, round(dw - 0.1), round(dh - 0.1)


def letterbox_tensor(img: Image.Image) -> np.ndarray:
    """(1,3,640,640) float32 RGB 0-1, square letterbox padded with 114."""
    from ultralytics.data.augment import LetterBox

    rgb = np.ascontiguousarray(np.asarray(img.convert("RGB")))
    lb = LetterBox(new_shape=(IMGSZ, IMGSZ), auto=False, stride=32, padding_value=PAD_VALUE)(
        image=rgb
    )
    return np.ascontiguousarray(lb.transpose(2, 0, 1)[None], dtype=np.float32) / 255.0


def unletterbox(boxes: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """xyxy in the 640 square -> xyxy in the original (w0, h0) image, clipped."""
    w0, h0 = size
    gain, left, top = letterbox_params(w0, h0)
    out = np.asarray(boxes, dtype=np.float32).copy()
    out[:, [0, 2]] = (out[:, [0, 2]] - left) / gain
    out[:, [1, 3]] = (out[:, [1, 3]] - top) / gain
    out[:, [0, 2]] = out[:, [0, 2]].clip(0, w0)
    out[:, [1, 3]] = out[:, [1, 3]].clip(0, h0)
    return out


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.clip(rb - lt, 0, None).prod(-1)
    area_a = np.clip(a[:, 2:] - a[:, :2], 0, None).prod(-1)
    area_b = np.clip(b[:, 2:] - b[:, :2], 0, None).prod(-1)
    return inter / np.maximum(area_a[:, None] + area_b[None] - inter, 1e-12)


def nms(boxes: np.ndarray, scores: np.ndarray, iou: float = IOU) -> list[int]:
    """Greedy class-agnostic NMS; returns kept indices, best score first."""
    order = list(np.argsort(-np.asarray(scores), kind="stable"))
    keep: list[int] = []
    while order:
        i = order.pop(0)
        keep.append(int(i))
        if order:
            ious = iou_matrix(boxes[i : i + 1], boxes[order])[0]
            order = [j for j, v in zip(order, ious, strict=True) if v <= iou]
    return keep


def concept_score(fp: np.ndarray, fp_scale: np.ndarray, fp_bias: np.ndarray, text: np.ndarray):
    """(N,512), (N,), (N,), (M,512) -> (N,M) = sigmoid(fp_scale * cos(fp, text) + fp_bias)."""
    z = fp_scale[:, None] * (_l2(fp) @ _l2(text).T) + fp_bias[:, None]
    return 1.0 / (1.0 + np.exp(-z))


def pad_prompts(pe: np.ndarray, n: int = 8) -> np.ndarray:
    """(M,512) -> (1,n,512), repeating the last row (the graph takes max over prompts)."""
    pe = np.asarray(pe, dtype=np.float32).reshape(-1, pe.shape[-1])
    if len(pe) > n:
        raise ValueError(f"at most {n} prompts, got {len(pe)}")
    return np.concatenate([pe, np.repeat(pe[-1:], n - len(pe), 0)])[None]


def select(
    boxes: np.ndarray, obj: np.ndarray, size: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Graph outputs (100,4)/(100,) -> (xyxy in image px, conf, kept row indices)."""
    keep = np.flatnonzero(obj >= CONF)
    xyxy = unletterbox(boxes[keep], size)
    wh = xyxy[:, 2:] - xyxy[:, :2]
    ok = (wh[:, 0] >= MIN_SIDE) & (wh[:, 1] >= MIN_SIDE)
    keep, xyxy = keep[ok], xyxy[ok]
    if len(keep):
        k = nms(xyxy, obj[keep], IOU)[:MAX_BOXES]
        keep, xyxy = keep[k], xyxy[k]
    return xyxy, obj[keep], keep


class OnnxFinder:
    def __init__(self, folder: Path = FORGE_DATA / "yoloe") -> None:
        self.folder = Path(folder)
        self._finder = None
        self._text = None
        self.proposal_pe = pad_prompts(np.load(PROPOSAL_PE))
        self.space_id = "yoloe-26s-mobileclip2-b"
        self.text_model_id = "mobileclip2-b-text"

    def _session(self, name: str):
        import onnxruntime as ort

        return ort.InferenceSession(str(self.folder / name), providers=["CPUExecutionProvider"])

    def run_raw(self, x: np.ndarray, pe: np.ndarray | None = None) -> list[np.ndarray]:
        """Graph outputs (boxes, objectness, fingerprint, fp_scale, fp_bias) for a (1,3,640,640)."""
        if self._finder is None:
            self._finder = self._session(FINDER_FILE)
        pe = self.proposal_pe if pe is None else pe
        return self._finder.run(None, {"images": x, "proposal_pe": pe})

    def _infer(self, img: Image.Image):
        boxes, obj, fp, scale, bias = self.run_raw(letterbox_tensor(img))
        xyxy, conf, keep = select(boxes[0], obj[0], img.size)
        return xyxy, conf, fp[0][keep], scale[0][keep], bias[0][keep]

    def boxes(self, img: Image.Image) -> list[dict]:
        xyxy, conf, *_ = self._infer(img)
        return Finder._regions(xyxy, conf, img.size)

    def box_embeddings(self, img: Image.Image) -> tuple[list[dict], np.ndarray]:
        xyxy, conf, fp, *_ = self._infer(img)
        return Finder._regions(xyxy, conf, img.size), _l2(fp)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """(M,512) L2, MobileCLIP2-B text encoder + the head's text branch (same as get_text_pe)."""
        import clip

        if self._text is None:
            self._text = self._session(TEXT_FILE)
        ids = clip.tokenize(list(texts), truncate=True).numpy().astype(np.int64)
        rows = [self._text.run(None, {"input_ids": ids[i : i + 1]})[0][0] for i in range(len(ids))]
        return _l2(np.stack(rows))


__all__ = ["OnnxFinder", "PROPOSAL_VOCAB"]
