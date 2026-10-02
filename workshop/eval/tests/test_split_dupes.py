"""dHash, near-dupe clusters and the 60/40 split on a balanced fixture."""

from __future__ import annotations

import json
from pathlib import Path

from workshop.eval import dupes, split


def test_dhash_shifted_copy_close_and_different_far(tmp_path: Path, img):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    base = img.texture(1)
    img.save(base, a)
    img.save(img.noisy_shift(base, 5), b)
    assert (dupes.dhash(a) ^ dupes.dhash(b)).bit_count() <= 20
    other = tmp_path / "c.png"
    img.save(img.texture(2), other)
    assert (dupes.dhash(a) ^ dupes.dhash(other)).bit_count() > 20


def test_split_balanced_with_dupes_on_one_side(tmp_path, labels_with_dupes, screens):
    lp, sp = tmp_path / "labels.json", tmp_path / "splits.json"
    lp.write_text(json.dumps(labels_with_dupes))
    assert (
        split.main(
            ["--labels", str(lp), "--screens", str(screens), "--seed", "12", "--out", str(sp)]
        )
        == 0
    )
    res = json.loads(sp.read_text())
    assert res["seed"] == 12 and res["hashBits"] == 256 and res["maxDist"] == 20
    assert len(res["dev"]) + len(res["test"]) == 77
    assert not set(res["dev"]) & set(res["test"])
    rep = split.report(labels_with_dupes, res)
    assert rep["problems"] == []
    for row in [*rep["classes"].values(), *rep["apps"].values()]:
        assert 55 <= row["devShare"] <= 65
    assert len(res["clusters"]) == 2
    for g in res["clusters"]:
        assert all(n in res["dev"] for n in g) or all(n in res["test"] for n in g)
    assert dupes.main(["--screens", str(screens), "--splits", str(sp)]) == 0
    # Move one image of a dupe pair across the line: the dupes check must fail.
    g = res["clusters"][0]
    side, other = ("dev", "test") if g[0] in res["dev"] else ("test", "dev")
    res[side].remove(g[0])
    res[other].append(g[0])
    sp.write_text(json.dumps(res))
    assert dupes.main(["--screens", str(screens), "--splits", str(sp)]) == 1


def test_split_reports_unbalanced_group():
    labels = [
        {"image": f"a-{i:04d}.png", "clean": True, "boxes": [], "meta": {"app": "x"}}
        for i in range(10)
    ]
    res = split.split(labels, None, 12)
    res["dev"], res["test"] = res["dev"] + res["test"][:2], res["test"][2:]
    assert split.report(labels, res)["problems"]
