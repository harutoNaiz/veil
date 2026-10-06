import json
import random

import numpy as np
import pytest
from PIL import Image

from workshop.twin.bench import compose, fmt, oi, select

LIC = "https://creativecommons.org/licenses/by/2.0/"


def _manifest():
    imgs = [
        {"id": "a", "pos": ["zebra"]},
        {"id": "b", "pos": []},
        {"id": "c", "pos": ["zebra"]},
    ]
    scr = [
        {
            "i": 0,
            "app": "x",
            "dark": True,
            "cards": ["a", "b", "c"],
            "photoRects": [{"x": 1, "y": 2, "w": 3, "h": 4}] * 3,
        }
    ]
    words = [{"word": "zebra", "category": "animal", "split": "test"}]
    return {"version": 1, "words": words, "images": imgs, "screens": scr}


def test_fmt_round_trip_and_tamper(tmp_path):
    m = _manifest()
    vecs = np.random.default_rng(0).normal(size=(22, 8)).astype(np.float32)
    h = fmt.write_bench(tmp_path, m, vecs, [{"regionId": "whole"}])
    b = fmt.load_bench(tmp_path)
    assert b.lock["manifestSha256"] == h == fmt.manifest_hash(m)
    assert fmt.screen_vecs(b, 0).shape == (22, 8) and fmt.screen_vecs(b, 0).dtype == np.float32
    lab = fmt.labels_for(b, "zebra")
    assert len(lab[0]["boxes"]) == 2 and not lab[0]["clean"]
    assert fmt.labels_for(b, "lion")[0]["clean"] is True
    m["images"][0]["pos"] = []
    (tmp_path / "manifest.json").write_bytes(fmt.canonical(m))
    with pytest.raises(ValueError):
        fmt.load_bench(tmp_path)


def test_flickr_id():
    assert oi.flickr_id("https://c2.staticflickr.com/6/5629/15340259497_0e3ee_o.jpg") == (
        "15340259497"
    )
    assert oi.flickr_id("http://x/y/abc.jpg") == ""
    assert oi.licence_ok(LIC)
    assert not oi.licence_ok("https://creativecommons.org/licenses/by-nc/2.0/")


def _fake(n_pos=6):
    classes = {
        "cat": ["/m/cat"],
        "zebra": ["/m/z"],
        "chair": ["/m/ch"],
        "lamp": ["/m/la"],
        "vase": ["/m/va"],
        "apple": ["/m/ap"],
        "car": ["/m/car"],
        "swimwear": ["/m/sw"],
        "drawing": ["/m/dr"],
    }
    cands = {
        "banned": ["cat"],
        "block": ["Swimwear"],
        "tags": ["Drawing"],
        "dev": [],
        "categories": {
            "animal": [{"word": "cat", "oi": "Cat"}, {"word": "zebra", "oi": "Zebra"}],
            "object": [{"word": w, "oi": w} for w in ("chair", "lamp", "vase")],
            "food": [{"word": "apple", "oi": "Apple"}],
            "vehicle": [{"word": "car", "oi": "Car"}],
        },
    }
    labels = {"pos": {}, "neg": {}, "anypos": set(), "tagMids": {"/m/dr": "Drawing"}}
    meta = {}
    for mid in ("/m/cat", "/m/z", "/m/ch", "/m/la", "/m/va", "/m/ap", "/m/car"):
        for k in range(n_pos):
            i = f"{mid[3:]}{k}"
            labels["pos"][i] = {mid}
            labels["anypos"].add(i)
            meta[i] = {
                "id": i,
                "subset": "validation",
                "url": f"http://h/{k}{mid[3:]}_x.jpg",
                "landing": "",
                "license": LIC,
                "author": "a",
                "rotation": 0,
            }
    labels["pos"]["z0"].add("/m/sw")  # BLOCK label -> dropped
    labels["neg"]["ch0"] = {"/m/z"}
    meta["ch0"]["url"] = "http://h/777_x.jpg"
    return cands, classes, labels, meta


PROF = {
    "per_cat": 2,
    "min_pos": 3,
    "dev": False,
    "q": (4, 2, 3),
    "quota": (2, 1, 2),
    "subsets": [],
    "dev_n": 0,
    "min_dev": 1,
}


def test_selection_rules():
    cands, classes, labels, meta = _fake()
    desc = {m[0]: {m[0]} for m in classes.values()}
    sel = select.build_selection(cands, PROF, classes, desc, labels, meta, set())
    words = [w["word"] for w in sel["words"]]
    assert "cat" not in words  # BANNED
    assert "z0" not in sel["queues"]["pos:zebra"]  # BLOCK label dropped
    # round robin: animal has 1 word, so it takes object's next word
    assert words.count("zebra") == 1
    assert len([w for w in words if w in ("chair", "lamp", "vase")]) == 3
    assert select.balance(sel["words"]) == {"animal": 1, "object": 3, "food": 1, "vehicle": 1}
    again = select.build_selection(cands, PROF, classes, desc, labels, meta, set())
    assert again["queues"] == sel["queues"]  # stable order
    q = sel["queues"]["pos:zebra"]
    assert q == sorted(q, key=lambda i: select.key("zebra", i))
    assert "ch0" in sel["queues"]["look:zebra"]
    assert not set(sel["queues"]["pool"]) & set(labels["pos"])  # pool has no candidate positives
    # an image whose Flickr id is in the bank is dropped
    sel2 = select.build_selection(cands, PROF, classes, desc, labels, meta, {"777"})
    assert "ch0" not in sel2["queues"]["look:zebra"]


def test_render_feed_deterministic():
    ph = [Image.new("RGB", (200 + 10 * k, 150), (30 * k, 90, 200)) for k in range(3)]
    a = compose.render_feed(random.Random(5), ph, True)
    b = compose.render_feed(random.Random(5), ph, True)
    assert a[1] == b[1] and a[2] == b[2] and a[0].tobytes() == b[0].tobytes()
    assert a[0].size == (360, 780) and len(a[1]) == 3
    ids = [f"i{k}" for k in range(7)]
    plan = compose.plan_screens(ids)
    assert plan == compose.plan_screens(ids[::-1])
    assert len(plan) == 3 and all(len(s["cards"]) == 3 for s in plan) and plan[0]["dark"]
    json.dumps(plan)
