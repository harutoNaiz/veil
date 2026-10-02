"""YOLOE object finder: boxes (variant C) and per-box fingerprints (variant B), SPEC 1.3.2.

Everything runs at runtime from the one checkpoint; the proposal vocabulary is fixed and is not
the user's list, so a new word never touches this model. The text side is YOLOE's OWN text encoder
(`get_text_pe`), which lives in the head's embedding space, so `embed_texts` is only comparable
with `box_embeddings`.

R-1: ultralytics downloads into the current directory, so model load and every text encode run
inside `contextlib.chdir(MODELS)`, and YOLO_AUTOINSTALL is forced off before ultralytics is
imported.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

import numpy as np
from PIL import Image

os.environ["YOLO_AUTOINSTALL"] = "False"  # ultralytics must never pip-install on its own

REPO = Path(__file__).resolve().parents[2]
MODELS = REPO / "data" / "models"
YOLOE_WEIGHTS = "yoloe-26s-seg.pt"
PROPOSAL_VOCAB = ["animal", "object", "toy", "drawing", "insect", "person", "food", "vehicle"]

CONF = 0.05
IOU = 0.5
IMGSZ = 640
MAX_BOXES = 20
MIN_SIDE = 24  # pixels, in the original image


def _l2(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


class Finder:
    """YOLOE-26s with a fixed text-prompted vocabulary. One instance serves every concept list."""

    def __init__(self, weights: str = YOLOE_WEIGHTS) -> None:
        import torch
        from ultralytics import YOLOE

        path = Path(weights)
        if not path.is_absolute():
            path = MODELS / path
        if not path.is_file():
            raise FileNotFoundError(f"YOLOE weights not found: {path} (never auto-downloaded here)")
        self.weights_path = path
        MODELS.mkdir(parents=True, exist_ok=True)
        with contextlib.chdir(MODELS):
            self.yolo = YOLOE(str(path))
            self._model = self.yolo.model
            names = list(PROPOSAL_VOCAB)
            self.yolo.set_classes(names, self._text_pe(names))  # runtime only, never an export
        self._model.fuse(verbose=False)  # removes the unused one2many branch; keeps the text head
        self._head = self._model.model[-1]
        text_model = str(
            getattr(self._model, "text_model", "mobileclip:blt")
        )  # e.g. "mobileclip2:b"
        base, _, size = text_model.partition(":")
        self.text_encoder = text_model
        stem = path.stem.removesuffix("-seg")
        self.space_id = f"{stem}-{base}-{size}".rstrip("-")  # "yoloe-26s-mobileclip2-b"
        self.text_model_id = f"{base}-{size}-text".replace("--", "-")
        self.dim = int(self._head.embed)
        self._torch = torch

    # ---- text side ----
    def _text_pe(self, texts: list[str]):
        """(1, N, D) text prompt embeddings, L2-normalised by the head's text branch."""
        return self._model.get_text_pe(list(texts), cache_clip_model=True)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        with contextlib.chdir(MODELS):
            pe = self._text_pe(texts)
        return _l2(pe.reshape(-1, pe.shape[-1]).float().cpu().numpy())

    @property
    def models(self) -> tuple[object, ...]:
        """The live model objects (for identity checks): the detector and its text encoder."""
        return (self._model, getattr(self._model, "clip_model", None))

    # ---- image side ----
    def _infer(self, img: Image.Image, want_emb: bool):
        """One forward pass: (xyxy px, conf, anchor index, per-anchor emb or None, size)."""
        torch = self._torch
        from torchvision.ops import nms
        from ultralytics.data.augment import LetterBox
        from ultralytics.utils import ops

        rgb = np.ascontiguousarray(np.asarray(img.convert("RGB")))
        h0, w0 = rgb.shape[:2]
        stride = int(self._model.stride.max())
        lb = LetterBox(new_shape=(IMGSZ, IMGSZ), auto=True, stride=stride)(image=rgb)
        x = torch.from_numpy(np.ascontiguousarray(lb)).permute(2, 0, 1)[None].float() / 255.0

        head = self._head
        end2end = bool(head.end2end)
        norms = (head.one2one_cv4 if end2end else head.cv4) if want_emb else []
        feats: list = []
        hooks = [m.norm.register_forward_hook(lambda _m, _i, o: feats.append(o)) for m in norms]
        kept: dict = {}
        orig = head.get_topk_index

        def grab(scores, max_det):
            out = orig(scores, max_det)
            kept["idx"] = out[2]
            return out

        if end2end:
            head.get_topk_index = grab
        try:
            with torch.inference_mode():
                out = self._model(x)
        finally:
            for h in hooks:
                h.remove()
            if end2end:
                del head.get_topk_index  # back to the class method

        y = out[0][0]
        if end2end:  # (1, k, 6+nm) [x1 y1 x2 y2 score cls ...], anchor ids from the top-k step
            det = y[0]
            boxes, conf = det[:, :4], det[:, 4]
            anchor = kept["idx"][0]
        else:  # (1, 4+nc+nm, A) xywh + class scores, every anchor is a candidate
            p = y[0].T
            cxcy, wh = p[:, :2], p[:, 2:4]
            boxes = torch.cat([cxcy - wh / 2, cxcy + wh / 2], 1)
            conf = p[:, 4 : 4 + head.nc].max(1).values
            anchor = torch.arange(p.shape[0])
        keep = conf >= CONF
        boxes, conf, anchor = boxes[keep], conf[keep], anchor[keep]
        boxes = ops.scale_boxes(lb.shape[:2], boxes.clone(), (h0, w0))
        wh = boxes[:, 2:] - boxes[:, :2]
        keep = (wh[:, 0] >= MIN_SIDE) & (wh[:, 1] >= MIN_SIDE)
        boxes, conf, anchor = boxes[keep], conf[keep], anchor[keep]
        if len(boxes):  # class-agnostic NMS also drops the same anchor listed under two classes
            keep = nms(boxes, conf, IOU)[:MAX_BOXES]
            boxes, conf, anchor = boxes[keep], conf[keep], anchor[keep]

        emb = None
        if want_emb:
            if len(feats) != len(norms) or not feats:
                raise NotImplementedError(f"hooks saw {len(feats)} levels, head has {len(norms)}")
            flat = torch.cat([f.flatten(2) for f in feats], dim=2)[0].T  # (A, D) in score order
            if len(anchor) and int(anchor.max()) >= flat.shape[0]:
                raise NotImplementedError("anchor index outside the embedding map (order mismatch)")
            emb = (
                _l2(flat[anchor].float().cpu().numpy())
                if len(anchor)
                else np.zeros((0, self.dim), np.float32)
            )
        return boxes.cpu().numpy(), conf.cpu().numpy(), anchor, emb, (w0, h0)

    @staticmethod
    def _regions(xyxy: np.ndarray, conf: np.ndarray, size: tuple[int, int]) -> list[dict]:
        w0, h0 = size
        regions = []
        for i, (b, c) in enumerate(zip(xyxy, conf, strict=True)):
            x1, y1 = max(0, int(np.floor(b[0]))), max(0, int(np.floor(b[1])))
            x2, y2 = min(w0, int(np.ceil(b[2]))), min(h0, int(np.ceil(b[3])))
            regions.append(
                {
                    "contractVersion": "1.0",
                    "regionId": f"o{i}",
                    "lookId": 0,
                    "tMs": 0,
                    "rect": {"x": x1, "y": y1, "w": max(1, x2 - x1), "h": max(1, y2 - y1)},
                    "source": "finder",
                    "kind": "object",
                    "objectness": float(min(1.0, max(0.0, c))),
                }
            )
        return regions

    def boxes(self, img: Image.Image) -> list[dict]:
        xyxy, conf, _, _, size = self._infer(img, want_emb=False)
        return self._regions(xyxy, conf, size)

    def box_embeddings(self, img: Image.Image) -> tuple[list[dict], np.ndarray]:
        """Variant B: the head's own per-anchor embedding (BN output of cv3, before the text dot).

        Cosine with `embed_texts` vectors equals the head's class score up to its fixed scale
        and bias. Raises NotImplementedError(reason) if the head layout is not the expected one.
        """
        xyxy, conf, _, emb, size = self._infer(img, want_emb=True)
        return self._regions(xyxy, conf, size), emb
