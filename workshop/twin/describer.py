"""Describer: SigLIP2 (base, patch16, 224) turns image pieces and words into 768-d fingerprints.

Weights load from the local Hugging Face cache only (HF_HUB_OFFLINE=1); this module never downloads.
torch and transformers are imported inside `Describer.__init__`, so importing this file is cheap.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

SPACE_ID = "siglip2-base-p16-224"
HF_ID = "google/siglip2-base-patch16-224"
TEXT_LEN = 64
DIM = 768


class TextEncoder(Protocol):
    space_id: str
    text_model_id: str

    def embed_texts(self, texts: list[str]) -> np.ndarray: ...


def hub_cache() -> Path:
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"])
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]) / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def weights_available() -> bool:
    """True when the SigLIP2 snapshot is complete in the local cache (never touches the network)."""
    root = hub_cache() / ("models--" + HF_ID.replace("/", "--"))
    if any((root / "blobs").glob("*.incomplete")):
        return False
    for snap in (root / "snapshots").glob("*"):
        has_tok = (snap / "tokenizer.json").is_file() or (snap / "tokenizer.model").is_file()
        if (
            (snap / "model.safetensors").is_file()
            and (snap / "preprocessor_config.json").is_file()
            and has_tok
        ):
            return True
    return False


def _pooled(out):
    """transformers 5 returns a pooled model output from get_*_features; older ones a tensor."""
    return out if hasattr(out, "dtype") else out.pooler_output


class Describer:
    space_id = SPACE_ID
    text_model_id = "siglip2-base-text"
    image_model_id = "siglip2-base-image"

    def __init__(self, device: str = "cpu") -> None:
        import torch
        from transformers import AutoModel, AutoProcessor

        self._torch = torch
        self.device = device
        self.model = AutoModel.from_pretrained(HF_ID).to(device).eval()
        self.processor = AutoProcessor.from_pretrained(HF_ID)

    def _norm(self, feats) -> np.ndarray:
        arr = feats.detach().float().cpu().numpy().astype(np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.maximum(norms, 1e-12)

    def embed_images(self, images: list[Image.Image], batch: int = 16) -> np.ndarray:
        """(N, 768) float32, L2-normalised."""
        if not images:
            return np.zeros((0, DIM), dtype=np.float32)
        rows = []
        with self._torch.inference_mode():
            for i in range(0, len(images), batch):
                chunk = [im.convert("RGB") for im in images[i : i + batch]]
                inputs = self.processor(images=chunk, return_tensors="pt")
                pixels = inputs["pixel_values"].to(self.device)
                rows.append(self._norm(_pooled(self.model.get_image_features(pixel_values=pixels))))
        return np.concatenate(rows, axis=0)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """(M, 768) float32, L2-normalised. SigLIP2 was trained on lower-case text padded to 64."""
        if not texts:
            return np.zeros((0, DIM), dtype=np.float32)
        tok = self.processor.tokenizer(
            [t.lower() for t in texts],
            padding="max_length",
            max_length=TEXT_LEN,
            truncation=True,
            return_tensors="pt",
        )
        with self._torch.inference_mode():
            ids = tok["input_ids"].to(self.device)
            return self._norm(_pooled(self.model.get_text_features(input_ids=ids)))
