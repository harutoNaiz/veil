"""public_set: composing screens from photos, truth, split. No network, no model weights."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from workshop.contracts.validate import validate
from workshop.twin import public_set


@pytest.fixture
def photos(tmp_path):
    root = tmp_path / "photos"
    for group, colour in {
        "cat": (200, 120, 60),
        "spider": (30, 30, 30),
        "dog": (120, 80, 40),
        "fox": (210, 90, 20),
        "neutral": (80, 160, 90),
    }.items():
        (root / group).mkdir(parents=True)
        for i in range(6 if group != "fox" else 2):
            Image.new("RGB", (320, 240 - 7 * i), colour).save(root / group / f"{group}-{i}.jpg")
    return root


def test_compose_truth_and_split(photos, tmp_path):
    out = tmp_path / "set"
    labels = public_set.compose(photos, out, n=20, seed=3)
    assert len(labels) == 20
    assert len(list(out.glob("*.png"))) == 20
    for lab in labels:
        validate("ScreenLabel", lab)
        image = Image.open(out / lab["image"])
        assert image.size == (lab["width"], lab["height"]) == public_set.SIZE
        for box in lab["boxes"]:
            r = box["rect"]
            assert r["x"] >= 0 and r["y"] >= 0
            assert r["x"] + r["w"] <= image.width and r["y"] + r["h"] <= image.height
        assert lab["clean"] == (not lab["boxes"])
    assert {"cats", "spiders"} == {b["concept"] for lab in labels for b in lab["boxes"]}
    assert all(lab["lookalikes"][0] in ("dog", "fox") for lab in labels if "lookalikes" in lab)
    splits = json.loads((out / "splits.json").read_text())
    assert set(splits["dev"]) | set(splits["test"]) == {lab["image"] for lab in labels}
    assert not set(splits["dev"]) & set(splits["test"])
    assert 0.5 <= len(splits["dev"]) / len(labels) <= 0.7


def test_compose_is_seeded(photos, tmp_path):
    first = public_set.compose(photos, tmp_path / "a", n=12, seed=5)
    second = public_set.compose(photos, tmp_path / "b", n=12, seed=5)
    assert first == second


def test_compose_without_photos_says_how_to_fetch(tmp_path):
    with pytest.raises(FileNotFoundError, match="--fetch"):
        public_set.compose(tmp_path / "none", tmp_path / "out")


def test_shrink_keeps_photos_small(tmp_path):
    import io
    import random

    rng = random.Random(1)
    noisy = Image.frombytes(
        "RGB", (900, 700), bytes(rng.randrange(256) for _ in range(900 * 700 * 3))
    )
    buf = io.BytesIO()
    noisy.save(buf, "PNG")
    small = public_set._shrink(buf.getvalue())
    assert len(small) <= public_set.MAX_BYTES
    assert max(Image.open(io.BytesIO(small)).size) <= public_set.MAX_SIDE
