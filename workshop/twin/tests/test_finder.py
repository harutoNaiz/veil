"""1.3.2 tests: YOLOE boxes and per-box vectors, the list switch, and the variant chooser.

YOLOE-only tests run on their own. Tests that need SigLIP2 or the 1.3.1 modules skip with a reason.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from workshop.contracts.validate import validate
from workshop.twin import variants
from workshop.twin.finder import MAX_BOXES, MIN_SIDE, MODELS, PROPOSAL_VOCAB, Finder

REPO = Path(__file__).resolve().parents[3]
SYNTH = REPO / "data" / "synth" / "1.2.1"
HF_HUB = Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub"
SIGLIP = HF_HUB / "models--google--siglip2-base-patch16-224"


def _have(mod: str) -> bool:
    return importlib.util.find_spec(f"workshop.twin.{mod}") is not None


def _siglip_ready() -> bool:
    return any(SIGLIP.glob("snapshots/*/model.safetensors"))  # a stale *.incomplete is harmless


def _images(n: int = 3) -> list[Image.Image]:
    imgs = [Image.open(p).convert("RGB") for p in sorted(SYNTH.glob("*.png"))[:n]]
    if imgs:
        return imgs
    im = Image.new("RGB", (360, 780), "white")  # fallback when the synthetic set is not generated
    d = ImageDraw.Draw(im)
    d.ellipse((60, 100, 300, 340), fill=(200, 120, 60))
    d.rectangle((40, 420, 320, 700), fill=(40, 90, 200))
    return [im]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _weight_files() -> list[Path]:
    files = [p for p in MODELS.glob("*") if p.suffix in {".pt", ".ts"}]
    files += list(SIGLIP.glob("snapshots/*/model.safetensors"))
    return files


@pytest.fixture(scope="module")
def finder() -> Finder:
    return Finder()


def test_boxes_are_valid_regions(finder):
    total = 0
    for img in _images():
        boxes = finder.boxes(img)
        assert len(boxes) <= MAX_BOXES
        total += len(boxes)
        for b in boxes:
            validate("Region", b)
            assert b["source"] == "finder" and b["kind"] == "object"
            r = b["rect"]
            assert 0 <= r["x"] and 0 <= r["y"]
            assert r["x"] + r["w"] <= img.width and r["y"] + r["h"] <= img.height
            assert r["w"] >= MIN_SIDE - 2 and r["h"] >= MIN_SIDE - 2  # rounding outward only widens
            assert 0.05 <= b["objectness"] <= 1.0
    print(f"boxes found over the test images: {total}")


def test_box_vectors_normalised_and_comparable_to_text(finder):
    texts = finder.embed_texts(["a photo of a cat", "a drawing of a spider"])
    assert texts.shape == (2, finder.dim)
    assert np.allclose(np.linalg.norm(texts, axis=1), 1.0, atol=1e-4)
    assert finder.space_id.startswith("yoloe-") and finder.text_model_id
    seen = 0
    for img in _images():
        try:
            regions, vecs = finder.box_embeddings(img)
        except NotImplementedError as exc:  # B not available: the reason goes to the record
            pytest.skip(f"variant B not available: {exc}")
        assert vecs.shape == (len(regions), finder.dim)
        assert vecs.dtype == np.float32
        if len(regions):
            assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-4)
            cos = vecs @ texts.T
            assert np.all(np.abs(cos) <= 1.0 + 1e-4)
            seen += len(regions)
    print(f"box vectors checked: {seen}")


def test_variant_b_scores_boxes_with_yoloes_text_side(finder):
    """B on a few images: boxes against YOLOE's own text vectors (1.3.1 judge if present)."""
    if _have("teacher") and _have("judge"):
        from workshop.twin.judge import judge
        from workshop.twin.teacher import compile_concept, concept_card

        cc = compile_concept(concept_card("cats"), finder, None, None)
    else:
        judge = cc = None
    for img in _images():
        try:
            regions, vecs = finder.box_embeddings(img)
        except NotImplementedError as exc:
            pytest.skip(f"variant B not available: {exc}")
        if not len(regions):
            continue
        if judge is not None:
            out = judge(vecs, cc, "balanced")
            assert len(out) == len(regions)
            assert all(0.0 <= v["probability"] <= 1.0 for v in out)
        else:
            cos = vecs @ finder.embed_texts(["a photo of a cat"]).T
            assert cos.shape == (len(regions), 1) and np.isfinite(cos).all()


def test_list_switch_finder_keeps_its_models_and_weights(finder):
    """cats -> spiders -> bicycles on one Finder: same model objects, same weight files."""
    before_ids = [id(m) for m in finder.models]
    before_sha = {p.name: _sha256(p) for p in _weight_files() if p.stat().st_size < 400e6}
    img = _images(1)[0]
    for word in ["cats", "spiders", "bicycles"]:
        vec = finder.embed_texts([f"a photo of a {word.rstrip('s')}"])
        assert vec.shape == (1, finder.dim)
        _, boxvecs = finder.box_embeddings(img)
        assert boxvecs.shape[1] == finder.dim
    assert [id(m) for m in finder.models] == before_ids
    assert {p.name: _sha256(p) for p in _weight_files() if p.stat().st_size < 400e6} == before_sha


@pytest.mark.skipif(
    not (_have("describer") and _have("teacher") and _have("judge")),
    reason="1.3.1 modules (describer/teacher/judge) not present yet",
)
def test_list_switch_with_describer_and_finder(finder):
    if not _siglip_ready():
        pytest.skip("SigLIP2 weights not fully downloaded yet")
    from workshop.twin.describer import Describer
    from workshop.twin.judge import judge
    from workshop.twin.teacher import compile_concept, concept_card

    desc = Describer()
    models = [id(desc), id(finder), *[id(m) for m in finder.models]]
    inner = [id(getattr(desc, a)) for a in ("model", "processor") if hasattr(desc, a)]
    shas = {p: _sha256(p) for p in _weight_files()}
    img = _images(1)[0]
    _, fvecs = finder.box_embeddings(img)
    dvecs = desc.embed_images([img])
    for word in ["cats", "spiders", "bicycles"]:
        card = concept_card(word)
        for enc, vecs in ((desc, dvecs), (finder, fvecs)):
            cc = compile_concept(card, enc, None, None)
            res = judge(vecs, cc, "balanced")
            assert len(res) == len(vecs) and all(
                r["decision"] in {"hide", "nearMiss", "leave"} for r in res
            )
    assert models == [id(desc), id(finder), *[id(m) for m in finder.models]]
    assert inner == [id(getattr(desc, a)) for a in ("model", "processor") if hasattr(desc, a)]
    assert shas == {p: _sha256(p) for p in _weight_files()}


def _row(variant, concept, recall, fc, sec, note=""):
    return {
        "variant": variant, "concept": concept, "recall": recall, "precision": 0.9,
        "cleanFalseCover": fc, "t": 0.5, "secPerScreen": sec, "note": note,
    }  # fmt: skip


def test_choose_and_best_point():
    pts = [
        {"t": 0.3, "recall": 0.95, "precision": 0.5, "cleanFalseCover": 0.30},
        {"t": 0.5, "recall": 0.80, "precision": 0.8, "cleanFalseCover": 0.05},
        {"t": 0.7, "recall": 0.40, "precision": 0.9, "cleanFalseCover": 0.00},
    ]
    best, ok = variants._best_point(pts)
    assert ok and best["t"] == 0.5
    best, ok = variants._best_point([pts[0]])
    assert not ok
    rows = [
        _row("A", "cats", 0.80, 0.04, 2.0), _row("A", "spiders", 0.60, 0.02, 2.0),
        _row("C", "cats", 0.80, 0.03, 3.0), _row("C", "spiders", 0.60, 0.03, 3.0),
        _row("B", "cats", None, None, None, "not run: no hook"),
    ]  # fmt: skip
    chosen, reason = variants.choose(rows)
    assert chosen == "A" and "faster" in reason  # tie on recall goes to the faster variant
    rows[2]["recall"] = 0.95
    rows[3]["recall"] = 0.90
    assert variants.choose(rows)[0] == "C"
    assert variants.choose([_row("A", "cats", None, None, None, "not run: x")])[0] is None
    md = variants.markdown({"rows": rows, "chosen": "C", "reason": "r"})
    assert "not run: no hook" in md and md.count("\n") >= len(rows)


def test_proposal_vocab_is_fixed():
    assert PROPOSAL_VOCAB == [
        "animal", "object", "toy", "drawing", "insect", "person", "food", "vehicle",
    ]  # fmt: skip
