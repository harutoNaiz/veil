"""7.2.3: replay set + AutoCalPipeline vs direct eval, on a tiny synthetic bench (no model)."""

from __future__ import annotations

import numpy as np
from PIL import Image

from workshop.contracts.rules import encode_f16
from workshop.replay.player import replay
from workshop.twin.bench import compare, fmt, replay_set
from workshop.twin.pieces import crop, make_pieces

RGB = {"r": (255, 0, 0), "g": (0, 255, 0), "b": (0, 0, 255), "k": (0, 0, 0)}
WORDS = [("red", "animal", "r"), ("green", "object", "g"), ("blue", "food", "b")]
SCREENS = ["rkk", "gkk", "bkk", "kkk", "rgk", "kbr"]
BAND = 260


class Stub:
    def embed_images(self, images):
        out = []
        for im in images:
            m = np.asarray(im.convert("RGB"), dtype=np.float64).mean(axis=(0, 1)) / 255 + 0.1
            out.append(m / np.linalg.norm(m))
        return np.asarray(out, dtype=np.float32)


def _vec(c: str) -> np.ndarray:
    v = np.asarray(RGB[c], dtype=np.float64) / 255 + 0.1
    return (v / np.linalg.norm(v)).astype(np.float32)


def _emb(c: str) -> dict:
    return {"dim": 3, "vectorF16": encode_f16(_vec(c))}


def _cc(c: str) -> dict:
    others = [_emb(o) for o in "rgb" if o != c]
    thr = {"light": 0.9, "balanced": 0.9, "strict": 0.9}
    return {"looksLike": [_emb(c)], "butNot": others, "thresholds": thr}


def _render(screen: dict, photos) -> Image.Image:
    img = Image.new("RGB", (360, 780), (0, 0, 0))
    for k, p in enumerate(photos):
        img.paste(p.resize((360, BAND)), (0, k * BAND))
    return img


def _make(tmp_path):
    for c, rgb in RGB.items():
        (tmp_path / "cache").mkdir(exist_ok=True)
        Image.new("RGB", (64, 64), rgb).save(tmp_path / "cache" / f"{c}.jpg", quality=95)
    images = [
        {"id": c, "pos": [w for w, _, cc in WORDS if cc == c], "neg": [], "roles": []} for c in RGB
    ]
    screens, vecs = [], []
    stub = Stub()
    for i, s in enumerate(SCREENS):
        rects = [{"x": 0, "y": k * BAND, "w": 360, "h": BAND} for k in range(3)]
        screens.append({"i": i, "app": "x", "dark": False, "cards": list(s), "photoRects": rects})
        img = _render(screens[-1], [Image.open(tmp_path / "cache" / f"{c}.jpg") for c in s])
        regions = make_pieces(img)
        vecs.append(stub.embed_images([crop(img, r["rect"]) for r in regions]))
    words = [{"word": w, "category": cat, "split": "test"} for w, cat, _ in WORDS]
    manifest = {"version": 1, "words": words, "images": images, "screens": screens}
    fmt.write_bench(tmp_path, manifest, np.concatenate(vecs), regions)
    return manifest


def test_phone10_order_deterministic():
    words = [
        {"word": f"{c}{k}", "category": c, "split": "test"}
        for c in ("animal", "object", "food", "vehicle")
        for k in range(4)
    ]
    m = {"words": words + [{"word": "dev1", "category": "animal", "split": "dev"}]}
    a = replay_set.phone10(m)
    assert a == replay_set.phone10(m)
    assert a[:5] == ["animal0", "object0", "food0", "vehicle0", "animal1"] and len(a) == 10


def test_replay_matches_direct(tmp_path):
    _make(tmp_path)
    sess = replay_set.build(tmp_path, render=_render)
    assert (tmp_path / "replay" / "replay-truth.json").exists()
    ccs = {w: _cc(c) for w, _, c in WORDS}
    pipe = replay_set.AutoCalPipeline(ccs, Stub())
    res = replay(sess, pipe, tmp_path / "out", video=False)
    assert res.frames == len(SCREENS)
    b = fmt.load_bench(tmp_path)
    import json

    truth = json.loads((tmp_path / "replay" / "replay-truth.json").read_text("utf-8"))
    worst = compare.compare(b, res.tape_out, ccs, truth)
    assert worst <= compare.MAX_DELTA
    direct = compare.direct_covers(b, ccs, "balanced", list(range(len(SCREENS))))
    assert {i for i, _ in direct["red"]} >= {0, 4, 5}  # the direct side really hides something
