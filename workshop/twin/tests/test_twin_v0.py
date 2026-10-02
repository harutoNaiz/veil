"""1.3.1 tests: cards, Judge maths, pieces, findings, data layer, plumbing with a stub encoder.

Everything except `test_describer_smoke` runs without model weights.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
from PIL import Image

from workshop.contracts.rules import check_rules
from workshop.contracts.validate import validate
from workshop.twin import data, gallery, judge, pieces, run, teacher
from workshop.twin.describer import weights_available


class StubEncoder:
    """Deterministic text fingerprints: unrelated phrases are nearly orthogonal."""

    space_id = "stub-space"
    text_model_id = "stub-text"
    image_model_id = "stub-image"

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        rows = []
        for text in texts:
            seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "little")
            vec = np.random.default_rng(seed).standard_normal(768)
            rows.append(vec / np.linalg.norm(vec))
        return np.asarray(rows, dtype=np.float32)


ENC = StubEncoder()


def compiled(word="cats", **calib) -> dict:
    doc = {"version": 1, "concepts": {teacher.concept_card(word)["conceptId"]: calib}}
    return teacher.compile_concept(teacher.concept_card(word), ENC, doc, None)


# ---------------------------------------------------------------- cards


@pytest.mark.parametrize("word", ["cats", "spiders", "snakes"])
def test_cards_validate(word):
    card = teacher.concept_card(word)
    validate("Concept", card)
    cc = teacher.compile_concept(card, ENC, None, None)
    validate("CompiledConcept", cc)
    check_rules("CompiledConcept", cc)
    singular = word[:-1]
    assert card["conceptId"] == word
    assert f"a photo of a {singular}" in card["looksLike"]
    assert len(cc["looksLike"]) == 5 and len(cc["ignore"]) == 3
    assert cc["spaceId"] == "stub-space" and cc["thresholds"] == {
        "light": 0.7,
        "balanced": 0.5,
        "strict": 0.3,
    }


def test_lookalikes_and_unknown_word():
    assert "a dog" in teacher.concept_card("cats")["butNot"]
    assert "a beetle" in teacher.concept_card("spiders")["butNot"]
    assert teacher.concept_card("snakes")["butNot"] == []
    with pytest.raises(ValueError):
        teacher.concept_card("???")


def test_calibration_and_thresholds_merge():
    calib = {"concepts": {"cats": {"calibrationOffset": -0.2, "butNotExtra": ["a tiger"]}}}
    thr = {"modes": {"light": 0.9, "balanced": 0.6, "strict": 0.4}, "margin": 0.05}
    cc = teacher.compile_concept(teacher.concept_card("cats"), ENC, calib, thr)
    validate("CompiledConcept", cc)
    assert cc["calibrationOffset"] == -0.2 and cc["margin"] == 0.05
    assert cc["thresholds"]["balanced"] == 0.6 and len(cc["butNot"]) == 5


def test_example_centroid_in_compiled_concept():
    centroid = ENC.embed_texts(["some photo"])[0]
    calib = {"concepts": {"cats": {"exampleThreshold": 0.8}}}
    cc = teacher.compile_concept(teacher.concept_card("cats"), ENC, calib, None, centroid)
    validate("CompiledConcept", cc)
    check_rules("CompiledConcept", cc)
    assert cc["exampleThreshold"] == 0.8 and cc["exampleCount"] == 1


# ---------------------------------------------------------------- Judge


def look_vec():
    return ENC.embed_texts(["a photo of a cat"])


def test_judge_hide_leave_nearmiss():
    cc = compiled()
    verdicts = judge.judge(np.concatenate([look_vec(), ENC.embed_texts(["text on a screen"])]), cc)
    assert [v["decision"] for v in verdicts] == ["hide", "leave"]
    assert verdicts[0]["probability"] > 0.99 and verdicts[0]["score"] == pytest.approx(1, abs=1e-3)
    # an offset pushes p below the threshold but inside the near-miss band (thr - 0.1)
    near = judge.judge(look_vec(), compiled(calibrationOffset=-0.55))[0]
    assert near["decision"] == "nearMiss" and 0.4 <= near["probability"] < 0.5


def test_margin_rule_blocks_a_hide():
    # a piece leaning slightly towards "cat" over "dog": margin about 0.07, probability high
    mix = 1.1 * ENC.embed_texts(["a photo of a cat"]) + ENC.embed_texts(["a dog"])
    mix = (mix / np.linalg.norm(mix)).astype(np.float32)
    cc = compiled()
    cc["margin"] = 0.2
    blocked = judge.judge(mix, cc)[0]
    assert 0.03 < blocked["margin"] < 0.2 and blocked["probability"] >= cc["thresholds"]["balanced"]
    assert blocked["decision"] == "nearMiss"
    assert judge.judge(mix, {**cc, "margin": 0.01})[0]["decision"] == "hide"


def test_example_rule_hides_without_text_match():
    centroid = ENC.embed_texts(["a specific cat"])[0]
    calib = {"concepts": {"cats": {"exampleThreshold": 0.9}}}
    cc = teacher.compile_concept(teacher.concept_card("cats"), ENC, calib, None, centroid)
    vec = np.stack([centroid, ENC.embed_texts(["a user interface"])[0]])
    assert [v["decision"] for v in judge.judge(vec, cc)] == ["hide", "leave"]


def test_empty_groups_use_minus_one():
    cc = compiled("snakes")
    cc["ignore"] = []
    v = judge.judge(ENC.embed_texts(["a photo of a snake"]), cc)[0]
    assert v["decision"] == "hide" and v["margin"] == pytest.approx(2, abs=1e-2)


def test_modes_use_their_thresholds():
    cc = compiled(calibrationOffset=-0.55)  # p = 0.45
    decisions = {m: judge.judge(look_vec(), cc, m)[0]["decision"] for m in judge.MODES}
    assert decisions == {"light": "leave", "balanced": "nearMiss", "strict": "hide"}


# ---------------------------------------------------------------- pieces and findings


@pytest.mark.parametrize("size", [(360, 780), (780, 360)])
def test_pieces_count_and_bounds(size):
    img = Image.new("RGB", size, (90, 90, 90))
    regions = pieces.make_pieces(img)
    assert len(regions) == 1 + 18 + 3
    assert len({r["regionId"] for r in regions}) == len(regions)
    assert [r["source"] for r in regions].count("tile") == 18
    for r in regions:
        validate("Region", r)
        x, y, w, h = (r["rect"][k] for k in "xywh")
        assert x >= 0 and y >= 0 and w >= 1 and h >= 1
        assert x + w <= size[0] and y + h <= size[1]
        assert pieces.crop(img, r["rect"]).size == (w, h)


def test_pieces_finder_boxes_and_no_tiles():
    img = Image.new("RGB", (360, 780))
    box = {
        "contractVersion": "1.0",
        "regionId": "b0",
        "lookId": 0,
        "tMs": 0,
        "rect": {"x": 10, "y": 10, "w": 50, "h": 50},
        "source": "finder",
        "kind": "object",
        "objectness": 0.9,
    }
    assert len(pieces.make_pieces(img, finder_boxes=[box])) == 23
    assert len(pieces.make_pieces(img, tiles=False)) == 4


def test_findings_validate_and_only_non_leave():
    regions = pieces.make_pieces(Image.new("RGB", (360, 780)))[:4]
    verdicts = [
        {"p_raw": 1.0, "probability": 1.0, "score": 1.0000001, "margin": 0.3, "decision": "hide"},
        {"p_raw": 0.4, "probability": 0.45, "score": 0.1, "margin": 0.0, "decision": "nearMiss"},
        {"p_raw": 0.0, "probability": 0.0, "score": 0.0, "margin": -0.2, "decision": "leave"},
        {"p_raw": 0.0, "probability": 0.0, "score": 0.0, "margin": -0.2, "decision": "leave"},
    ]
    found = judge.to_findings("a-0001.png", regions, verdicts, "cats", "describer")
    assert [f["decision"] for f in found] == ["hide", "nearMiss"]
    for f in found:
        validate("Finding", f)
        assert f["layer"] == 2 and f["scope"] == "object" and f["image"] == "a-0001.png"
    assert found[0]["findingId"] == "f0-whole" and found[0]["score"] == 1.0


# ---------------------------------------------------------------- data layer


def test_log_test_run_refuses_a_fourth(tmp_path):
    log = tmp_path / "test-runs.jsonl"
    assert [data.log_test_run("synthetic", f"run {i}", path=log) for i in range(3)] == [1, 2, 3]
    with pytest.raises(RuntimeError):
        data.log_test_run("synthetic", "one too many", path=log)
    assert data.log_test_run("public", "other set", path=log) == 1  # limits are per set
    rows = [json.loads(x) for x in log.read_text().splitlines()]
    assert len(rows) == 4 and {"set", "n", "utc", "note"} <= set(rows[0])


def test_load_folder(tmp_path):
    for name in ("b.png", "a.jpg", "notes.txt"):
        (tmp_path / name).write_bytes(b"x")
    assert [s.image.name for s in data.load_folder(tmp_path)] == ["a.jpg", "b.png"]
    assert all(s.label is None for s in data.load_folder(tmp_path))


def test_load_synthetic_split():
    dev, test = data.load_split("synthetic", "dev"), data.load_split("synthetic", "test")
    assert dev and test and not {s.image.name for s in dev} & {s.image.name for s in test}
    assert all(s.label is not None and s.image.is_file() for s in dev + test)
    assert 0.5 <= len(dev) / (len(dev) + len(test)) <= 0.7
    with pytest.raises(ValueError):
        data.load_split("synthetic", "val")


# ---------------------------------------------------------------- plumbing with a stub model


def stub_piece_fn(_screen, img):
    """Crop c0 looks like "a photo of a cat"; every other piece looks like an app screenshot."""
    regions = pieces.make_pieces(img)
    vecs = np.repeat(ENC.embed_texts(["a screenshot of an app"]), len(regions), axis=0)
    vecs[[r["regionId"] for r in regions].index("c0")] = look_vec()[0]
    return regions, vecs


def test_run_screens_cache_scores_and_gallery(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "CACHE", tmp_path / "cache")
    screens = data.load_split("synthetic", "dev")[:6]
    scores, fbc = run.run_screens(
        screens,
        ["cats", "spiders"],
        "stub-dev-A",
        out=tmp_path / "out",
        piece_fn=stub_piece_fn,
        encoder=ENC,
    )
    for word in ("cats", "spiders"):
        assert set(scores[word]) >= {"recall", "precision", "cleanFalseCover"}
        assert 0.0 <= scores[word]["cleanFalseCover"] <= 1.0
        assert len(list((tmp_path / "out" / word).glob("*.json"))) == len(screens)
        for found in fbc[word].values():
            for f in found:
                validate("Finding", f)
    assert scores["cats"]["covers"] == len(screens)  # one hide per screen (crop c0)
    assert len(list((tmp_path / "cache" / "stub-dev-A").glob("*.npz"))) == len(screens)
    # a second run reads the cache: same numbers, no model call
    again, _ = run.run_screens(
        screens, ["cats"], "stub-dev-A", piece_fn=lambda *_: pytest.fail("cache miss"), encoder=ENC
    )
    assert again["cats"] == scores["cats"]
    index = gallery.build_gallery(screens, fbc, tmp_path / "gal" / "index.html")
    text = index.read_text(encoding="utf-8")
    assert text.count("<img") == len(screens) and "TP " in text
    assert len(list((tmp_path / "gal" / "thumbs").glob("*.jpg"))) == len(screens)


def test_sweep_grid_and_dev_only(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "CACHE", tmp_path / "cache")
    ccs = {"cats": teacher.compile_concept(teacher.concept_card("cats"), ENC, None, None)}
    rows = run.sweep("synthetic", "dev", "cats", "stub", ccs, piece_fn=stub_piece_fn, encoder=ENC)
    assert [r["t"] for r in rows] == [round(0.05 * k, 2) for k in range(1, 20)]
    assert all(0.0 <= r["cleanFalseCover"] <= 1.0 for r in rows)
    with pytest.raises(ValueError):
        run.sweep("synthetic", "test", "cats", "stub", ccs, piece_fn=stub_piece_fn, encoder=ENC)


def test_score_findings_matches_scorer_by_hand():
    rect = {"x": 0, "y": 0, "w": 100, "h": 100}
    base = {"contractVersion": "1.0", "width": 360, "height": 780, "meta": {}, "labeller": "t"}
    screens = [
        data.Screen(
            run.Path("a.png"),
            {
                **base,
                "image": "a.png",
                "clean": False,
                "boxes": [{"concept": "cats", "rect": rect}],
            },
        ),
        data.Screen(run.Path("b.png"), {**base, "image": "b.png", "clean": True, "boxes": []}),
    ]

    def finding(image, decision):
        return {"conceptId": "cats", "decision": decision, "rect": rect, "image": image}

    found = {"a.png": [finding("a.png", "hide")], "b.png": [finding("b.png", "nearMiss")]}
    s = run.score_findings(screens, found, "cats")
    assert (s["recall"], s["precision"], s["cleanFalseCover"]) == (1.0, 1.0, 0.0)
    found["b.png"] = [finding("b.png", "hide")]
    s = run.score_findings(screens, found, "cats")
    assert (s["recall"], s["precision"], s["cleanFalseCover"]) == (1.0, 0.5, 1.0)


# ---------------------------------------------------------------- real model


@pytest.mark.skipif(not weights_available(), reason="WEIGHTS PENDING: SigLIP2 not in the HF cache")
def test_describer_smoke():
    from workshop.twin.describer import Describer

    d = Describer()
    texts = d.embed_texts(["a photo of a cat"])
    assert texts.shape == (1, 768) and np.linalg.norm(texts[0]) == pytest.approx(1, abs=1e-4)
    imgs = d.embed_images([Image.new("RGB", (120, 90), (200, 120, 60))] * 3, batch=2)
    assert imgs.shape == (3, 768) and np.allclose(np.linalg.norm(imgs, axis=1), 1, atol=1e-4)


def test_corrupt_cache_entry_is_recomputed(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "CACHE", tmp_path / "cache")
    screens = data.load_split("synthetic", "dev")[:1]
    bad = tmp_path / "cache" / "k" / f"{screens[0].image.stem}.npz"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"PK garbage")
    out = run.embed_set(screens, stub_piece_fn, "k")
    assert len(out) == 1 and out[0][1].shape[1] == 768
    assert run._load_cache(bad, run._sig(screens[0].image)) is not None
