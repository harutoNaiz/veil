from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from workshop.contracts.validate import validate
from workshop.screens import synth


@pytest.fixture(scope="module")
def out(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("synth")
    synth.generate(path, n=75, near_dupes=2, seed=7)
    return path


@pytest.fixture(scope="module")
def truth(out: Path) -> list[dict]:
    return json.loads((out / "truth.json").read_text(encoding="utf-8"))


def _classes(labels: list[dict]) -> Counter:
    def cls(label: dict) -> str:
        concepts = {b["concept"] for b in label["boxes"]}
        return "cats" if "cats" in concepts else "spiders" if "spiders" in concepts else "clean"

    return Counter(cls(label) for label in labels)


def test_files_truth_and_counts(out: Path, truth: list[dict]) -> None:
    assert len(list(out.glob("*.png"))) == 77
    assert len(list(out.glob("*-dup.png"))) == 2
    assert len(truth) == 77
    originals = truth[:75]
    for label in truth:
        validate("ScreenLabel", label)
        with Image.open(out / label["image"]) as im:
            assert im.size == (label["width"], label["height"])
    assert _classes(originals) == {"cats": 25, "spiders": 25, "clean": 25}
    assert len({label["meta"]["app"] for label in originals}) == 5
    assert sum(label["meta"]["mode"] == "dark" for label in originals) >= 0.2 * 75
    assert sum(label["meta"]["orientation"] == "landscape" for label in originals) == 5
    assert any(label.get("lookalikes") == ["dog"] for label in originals)
    assert any(b.get("tag") == "cat-emoji" for label in originals for b in label["boxes"])


def test_boxes_inside_image_and_not_overlapping(truth: list[dict]) -> None:
    for label in truth:
        rects = [b["rect"] for b in label["boxes"]]
        for r in rects:
            assert r["x"] >= 0 and r["y"] >= 0
            assert r["x"] + r["w"] <= label["width"] and r["y"] + r["h"] <= label["height"]
        for a, b in itertools.combinations(rects, 2):
            apart = (
                a["x"] + a["w"] <= b["x"]
                or b["x"] + b["w"] <= a["x"]
                or a["y"] + a["h"] <= b["y"]
                or b["y"] + b["h"] <= a["y"]
            )
            assert apart, label["image"]


def _dhash(path: Path) -> np.ndarray:
    # same recipe as the 1.2.3 dupes tool: grayscale, 17x16, compare adjacent columns
    with Image.open(path) as im:
        px = np.asarray(im.convert("L").resize((17, 16), Image.Resampling.BOX), dtype=np.int16)
    return (px[:, :-1] > px[:, 1:]).ravel()


def test_dhash_separates_unrelated_images_and_keeps_dupes_close(
    out: Path, truth: list[dict]
) -> None:
    hashes = {label["image"]: _dhash(out / label["image"]) for label in truth}
    names = [label["image"] for label in truth[:75]]
    assert (
        min(int((hashes[a] != hashes[b]).sum()) for a, b in itertools.combinations(names, 2)) > 40
    )
    for label in truth[75:]:
        original = label["image"].replace("-dup", "")
        assert int((hashes[label["image"]] != hashes[original]).sum()) <= 12


def test_deterministic_and_refuses_foreign_folder(tmp_path: Path) -> None:
    a = synth.generate(tmp_path / "a", n=6, near_dupes=1, seed=3)
    b = synth.generate(tmp_path / "b", n=6, near_dupes=1, seed=3)
    assert a == b
    assert (tmp_path / "a" / a[0]["image"]).read_bytes() == (
        tmp_path / "b" / a[0]["image"]
    ).read_bytes()
    foreign = tmp_path / "real"
    foreign.mkdir()
    Image.new("RGB", (4, 4)).save(foreign / "keep-me-0001.png")
    with pytest.raises(ValueError, match="refusing"):
        synth.generate(foreign, n=3, near_dupes=0)
    assert (foreign / "keep-me-0001.png").exists()
