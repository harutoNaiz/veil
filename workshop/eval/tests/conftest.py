"""Shared fixtures: a balanced 75-entry label set and textured PNGs (no dependency on 1.2.1)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

APPS = ["instagram", "youtube", "chrome", "whatsapp", "x"]


def make_labels(n: int = 75) -> list[dict]:
    labels = []
    for i in range(n):
        cls = ["cats", "spiders", "clean"][(i // 5) % 3]
        land = i % 15 == 14
        w, h = (780, 360) if land else (360, 780)
        boxes, lookalikes = [], []
        if cls == "cats":
            for k in range(1 + i % 3):
                boxes.append(_box("cats", "photo", k, None))
            if i % 5 == 0:
                boxes.append(_box("cats", "emoji", 3, "cat-emoji"))
        elif cls == "spiders":
            for k in range(1 + i % 2):
                boxes.append(_box("spiders", "photo", k, None))
        elif i % 2 == 0:
            lookalikes = ["dog"]
        labels.append(
            {
                "contractVersion": "1.0",
                "image": f"{APPS[i % 5]}-feed-{i:04d}.png",
                "width": w,
                "height": h,
                "clean": cls == "clean",
                "boxes": boxes,
                "lookalikes": lookalikes,
                "meta": {
                    "app": APPS[i % 5],
                    "surface": "feed",
                    "mode": "dark" if i % 3 == 0 else "light",
                    "orientation": "landscape" if land else "portrait",
                    "source": "synth",
                },
                "labeller": "synth",
            }
        )
    return labels


def _box(concept: str, kind: str, k: int, tag: str | None) -> dict:
    box = {
        "rect": {"x": 10 + 60 * k, "y": 20 + 120 * k, "w": 50, "h": 50},
        "concept": concept,
        "kind": kind,
        "scope": "object",
    }
    if tag:
        box["tag"] = tag
    return box


def texture(seed: int, size: tuple[int, int] = (360, 780)) -> np.ndarray:
    """A random blocky grey image (30 px blocks) so unrelated images hash far apart."""
    rng = np.random.default_rng(seed)
    w, h = size
    blocks = rng.integers(0, 256, size=(h // 30 + 1, w // 30 + 1), dtype=np.uint8)
    return np.kron(blocks, np.ones((30, 30), dtype=np.uint8))[:h, :w]


def noisy_shift(arr: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    moved = np.roll(arr, 2, axis=(0, 1)).astype(int) + rng.integers(-3, 4, size=arr.shape)
    return np.clip(moved, 0, 255).astype(np.uint8)


def save(arr: np.ndarray, path: Path) -> None:
    Image.fromarray(arr, mode="L").save(path)


@pytest.fixture
def labels() -> list[dict]:
    return make_labels()


@pytest.fixture
def screens(tmp_path: Path, labels: list[dict]) -> Path:
    """PNGs for the 75 labels plus 2 near-dupes of the first two (labels copied by tests)."""
    d = tmp_path / "screens"
    d.mkdir()
    for i, lab in enumerate(labels):
        save(texture(i), d / lab["image"])
    for i in range(2):
        save(noisy_shift(texture(i), 100 + i), d / (labels[i]["image"][:-4] + "-dup.png"))
    return d


@pytest.fixture
def labels_with_dupes(labels: list[dict]) -> list[dict]:
    dupes = []
    for lab in labels[:2]:
        d = json.loads(json.dumps(lab))
        d["image"] = lab["image"][:-4] + "-dup.png"
        dupes.append(d)
    return labels + dupes


@pytest.fixture
def img() -> SimpleNamespace:
    return SimpleNamespace(texture=texture, noisy_shift=noisy_shift, save=save)
