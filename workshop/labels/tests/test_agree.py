from __future__ import annotations

import json

from workshop.labels import agree


def _entry(name, rects):
    boxes = [
        {
            "rect": {"x": x, "y": y, "w": w, "h": h},
            "concept": "cats",
            "kind": "photo",
            "scope": "object",
        }
        for x, y, w, h in rects
    ]
    return {"image": name, "clean": not boxes, "boxes": boxes}


def _twenty_boxes(n_images=10):
    """n_images images with 2 well-separated boxes each: 20 items in total."""
    return [_entry(f"i{i}.png", [(0, 0, 100, 100), (200, 0, 100, 100)]) for i in range(n_images)]


def test_identical_passes_with_rate_zero():
    official = _twenty_boxes()
    report = agree.compare(official, json.loads(json.dumps(official)))
    assert (report["items"], report["rate"], report["coverage"], report["pass"]) == (
        20,
        0.0,
        1.0,
        True,
    )


def test_one_missing_box_of_20_passes_two_fail():
    official = _twenty_boxes()
    blind = json.loads(json.dumps(official))
    blind[0]["boxes"].pop()
    one = agree.compare(official, blind)
    assert (one["items"], one["disagreements"], one["rate"], one["pass"]) == (20, 1, 0.05, True)
    blind[1]["boxes"].pop()
    two = agree.compare(official, blind)
    assert (two["disagreements"], two["rate"], two["pass"]) == (2, 0.1, False)


def test_extra_box_and_low_iou_pair_count_as_disagreements():
    official = [_entry("a.png", [(0, 0, 100, 100)])]
    low = agree.compare(official, [_entry("a.png", [(0, 0, 100, 49)])])  # IoU 0.49
    assert (low["items"], low["disagreements"]) == (1, 1)
    ok = agree.compare(official, [_entry("a.png", [(0, 0, 100, 50)])])  # IoU 0.50
    assert (ok["items"], ok["disagreements"]) == (1, 0)
    extra = agree.compare(official, [_entry("a.png", [(0, 0, 100, 100), (500, 500, 10, 10)])])
    assert (extra["items"], extra["disagreements"]) == (2, 1)


def test_coverage_below_20_percent_fails():
    official = _twenty_boxes(10)
    report = agree.compare(official, official[:1])  # 1 of 10 images
    assert report["coverage"] == 0.1 and report["rate"] == 0.0 and report["pass"] is False


def test_sample_is_ceil_and_seeded(tmp_path):
    names = [f"n{i}.png" for i in range(300)]
    a = agree.sample(names, 0.1, 5)
    assert len(a) == 30 and a == agree.sample(names, 0.1, 5) and a != agree.sample(names, 0.1, 6)
    assert len(agree.sample(names[:7], 0.2, 1)) == 2
    labels = tmp_path / "l.json"
    labels.write_text(json.dumps([_entry(n, []) for n in names]), encoding="utf-8")
    out = tmp_path / "names.txt"
    assert (
        agree.main(
            [
                "sample",
                "--labels",
                str(labels),
                "--fraction",
                "0.2",
                "--seed",
                "3",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert len(out.read_text(encoding="utf-8").split()) == 60
