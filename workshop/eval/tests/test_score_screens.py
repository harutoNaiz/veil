"""Scorer: hand-worked case, boundary, perfect/empty/mistakes predictions."""

from __future__ import annotations

import json
from pathlib import Path

from workshop.eval import fake_preds, score_screens
from workshop.eval.score_screens import contains_frac, hits, iou, score


def R(x, y, w, h):
    return {"x": x, "y": y, "w": w, "h": h}


def lab(image, boxes=(), clean=False, lookalikes=()):
    return {
        "contractVersion": "1.0",
        "image": image,
        "width": 360,
        "height": 780,
        "clean": clean,
        "boxes": [
            {"rect": R(*r), "concept": c, "kind": "photo", "scope": "object"} for c, r in boxes
        ],
        "lookalikes": list(lookalikes),
    }


def fnd(i, image, concept, rect, decision="hide"):
    return {
        "contractVersion": "1.0",
        "findingId": f"f-{i}",
        "lookId": 0,
        "tMs": 0,
        "image": image,
        "rect": R(*rect),
        "conceptId": concept,
        "layer": 2,
        "lane": "finder",
        "decision": decision,
        "probability": 1.0,
        "scope": "object",
    }


def test_hand_worked_five_image_case():
    labels = [
        lab("s1.png", [("cats", (0, 0, 100, 100)), ("cats", (200, 0, 100, 100))]),
        lab("s2.png", [("cats", (0, 0, 100, 100))], lookalikes=["dog"]),
        lab("s3.png", [("spiders", (0, 0, 50, 50))]),
        lab("s4.png", clean=True),
        lab("s5.png", clean=True),
    ]
    preds = [
        fnd(1, "s1.png", "cats", (0, 0, 100, 100)),
        fnd(2, "s1.png", "cats", (150, -50, 250, 250)),
        fnd(3, "s2.png", "cats", (60, 60, 100, 100)),
        fnd(4, "s3.png", "spiders", (0, 0, 40, 50)),
        fnd(5, "s4.png", "cats", (10, 10, 50, 50)),
        fnd(6, "s5.png", "cats", (0, 0, 10, 10), decision="leave"),
    ]
    res = score(labels, preds)
    cats, spiders = res["concepts"]["cats"], res["concepts"]["spiders"]
    assert (cats["labels"], cats["hit"], cats["covers"], cats["correctCovers"]) == (3, 2, 4, 2)
    assert cats["recall"] == 2 / 3 and cats["precision"] == 0.5 and cats["cleanFalseCover"] == 0.5
    assert (spiders["labels"], spiders["hit"], spiders["covers"]) == (1, 1, 1)
    assert spiders["recall"] == 1.0 and spiders["precision"] == 1.0
    assert spiders["cleanFalseCover"] == 0.0
    assert res["cleanFalseCover"] == 0.5 and res["cleanImages"] == 2
    assert res["images"] == 5 and res["droppedPredictions"] == 1


def test_boundary_is_inclusive():
    label = R(0, 0, 100, 100)
    assert iou(R(0, 0, 30, 100), label) == 0.3 and hits(R(0, 0, 30, 100), label)
    assert not hits(R(0, 0, 25, 100), label)
    assert contains_frac(R(0, 0, 100, 70), label) == 0.7 and hits(R(0, 0, 100, 70), label)


def test_ignore_tag_leaves_denominators(labels):
    labels = [lab_ for lab_ in labels if lab_["boxes"]]
    emoji = [b for lab_ in labels for b in lab_["boxes"] if b.get("tag") == "cat-emoji"]
    perfect = fake_preds.make("perfect", labels)
    full = score(labels, perfect)["concepts"]["cats"]
    ign = score(labels, perfect, frozenset({"cat-emoji"}))["concepts"]["cats"]
    assert full["labels"] - ign["labels"] == len(emoji) > 0
    assert ign["recall"] == 1.0 and ign["precision"] == 1.0


def test_perfect_empty_and_mistakes(tmp_path: Path, labels):
    cats = sum(1 for lab_ in labels for b in lab_["boxes"] if b["concept"] == "cats")
    clean = sum(1 for lab_ in labels if lab_["clean"])
    perfect = score(labels, fake_preds.make("perfect", labels))
    for c in perfect["concepts"].values():
        assert c["recall"] == 1.0 and c["precision"] == 1.0 and c["cleanFalseCover"] == 0
    assert perfect["cleanFalseCover"] == 0
    empty = score(labels, fake_preds.make("empty", labels))
    for c in empty["concepts"].values():
        assert c["recall"] == 0.0 and c["cleanFalseCover"] == 0 and c["precision"] is None
    mist = score(labels, fake_preds.make("mistakes", labels, seed=3))
    assert mist["concepts"]["cats"]["recall"] == (cats - 2) / cats
    assert mist["concepts"]["cats"]["precision"] == (cats - 2) / cats
    assert mist["concepts"]["spiders"]["recall"] == 1.0
    assert mist["cleanFalseCover"] == 2 / clean


def test_cli_exit_codes(tmp_path: Path, labels):
    lp, pp = tmp_path / "l.json", tmp_path / "p.json"
    lp.write_text(json.dumps(labels))
    pp.write_text(json.dumps(fake_preds.make("perfect", labels)))
    args = ["--labels", str(lp), "--preds", str(pp)]
    assert score_screens.main(args + ["--out", str(tmp_path / "s.json")]) == 0
    assert json.loads((tmp_path / "s.json").read_text())["images"] == 75
    bad = fake_preds.make("perfect", labels)
    del bad[0]["image"]
    pp.write_text(json.dumps(bad))
    assert score_screens.main(args) == 2
