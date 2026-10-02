"""OnnxDescriber: the 1.3 Describer surface, backed by the exported SigLIP2 ONNX files (CPU)."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from workshop.forge.common import FORGE_DATA  # noqa: E402

SPACE_ID = "siglip2-base-p16-224"
HF_ID = "google/siglip2-base-patch16-224"
TEXT_LEN = 64
DIM = 768
BATCHES = (1, 4, 16)


def pick_batch(n: int) -> int:
    """Smallest exported batch size that holds n images (n <= 16)."""
    return next(b for b in BATCHES if n <= b)


def _l2(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float32)
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-12)


class OnnxDescriber:
    space_id = SPACE_ID
    text_model_id = "siglip2-base-text"
    image_model_id = "siglip2-base-image"

    def __init__(
        self, folder: Path = FORGE_DATA / "siglip2", sessions=None, processor=None
    ) -> None:
        self.folder = Path(folder)
        self._sessions = dict(sessions) if sessions else {}  # keys: b1, b4, b16, text
        self._processor = processor

    def _session(self, key: str):
        if key not in self._sessions:
            import onnxruntime as ort

            name = "siglip2-text.onnx" if key == "text" else f"siglip2-image-{key}.onnx"
            self._sessions[key] = ort.InferenceSession(
                str(self.folder / name), providers=["CPUExecutionProvider"]
            )
        return self._sessions[key]

    @property
    def processor(self):
        if self._processor is None:
            from transformers import AutoProcessor

            self._processor = AutoProcessor.from_pretrained(HF_ID)
        return self._processor

    def _pixels(self, chunk: list[Image.Image]) -> np.ndarray:
        px = self.processor(images=[im.convert("RGB") for im in chunk], return_tensors="np")
        return np.asarray(px["pixel_values"], dtype=np.float32)

    def _run_chunk(self, pixels: np.ndarray) -> np.ndarray:
        n = pixels.shape[0]
        b = pick_batch(n)
        if n < b:  # pad the last chunk by repeating the final row; drop the extra outputs
            pad = np.repeat(pixels[-1:], b - n, axis=0)
            pixels = np.concatenate([pixels, pad], axis=0)
        out = self._session(f"b{b}").run(["fingerprint"], {"pixel_values": pixels})[0]
        return np.asarray(out)[:n]

    def embed_images(self, images: list[Image.Image], batch: int = 16) -> np.ndarray:
        """(N, 768) float32, L2-normalised."""
        if not images:
            return np.zeros((0, DIM), dtype=np.float32)
        step = max(1, min(int(batch), BATCHES[-1]))
        rows = [
            self._run_chunk(self._pixels(images[i : i + step])) for i in range(0, len(images), step)
        ]
        return _l2(np.concatenate(rows, axis=0))

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """(M, 768) float32, L2-normalised; lower-case, padded to 64."""
        if not texts:
            return np.zeros((0, DIM), dtype=np.float32)
        tok = self.processor.tokenizer(
            [t.lower() for t in texts],
            padding="max_length",
            max_length=TEXT_LEN,
            truncation=True,
            return_tensors="np",
        )
        ids = np.asarray(tok["input_ids"], dtype=np.int64)
        sess = self._session("text")
        rows = [
            sess.run(["fingerprint"], {"input_ids": ids[i : i + 1]})[0] for i in range(len(ids))
        ]
        return _l2(np.concatenate(rows, axis=0))
