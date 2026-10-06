"""7.2.2 tests: synthetic 6-screen bench (dim 32), stub encoder/judge, no model."""

from __future__ import annotations

import numpy as np
import pytest

from workshop.twin.bench import attempts, evaluate, fmt, word_params_check

DIM = 32
W, H = 360, 240


def _cc(word: str) -> dict:
    q = np.zeros(DIM, dtype=np.float32)
    q[{"alpha": 0, "beta": 1}[word]] = 1.0
    return {"conceptId": f"c-{word}", "q": q}


def _judge(vecs, cc, mode="balanced"):
    out = []
    for s in np.asarray(vecs) @ cc["q"]:
        hide = bool(s > 0.5)
        out.append(
            {
                "decision": "hide" if hide else "leave",
                "probability": 0.9 if hide else 0.1,
                "score": float(s),
                "margin": 0.0,
            }
        )
    return out


@pytest.fixture()
def bench(tmp_path):
    images, screens = [], []
    for s in range(6):
        cards = []
        for c in range(3):
            iid = f"i{s}{c}"
            im = {"id": iid, "pos": [], "neg": [], "roles": ["pool"], "tags": []}
            cards.append(iid)
            images.append(im)
        screens.append(
            {
                "i": s,
                "app": "x",
                "dark": False,
                "cards": cards,
                "photoRects": [{"x": 0, "y": c * 250, "w": W, "h": H} for c in range(3)],
            }
        )
    by = {im["id"]: im for im in images}
    for s in range(4):
        by[f"i{s}0"]["pos"] = ["alpha"]
    by["i30"]["tags"] = ["Drawing"]
    by["i40"]["pos"] = ["beta"]
    by["i50"]["pos"] = ["beta"]
    by["i51"]["neg"] = ["alpha"]
    by["i42"]["neg"] = ["alpha"]
    words = [
        {"word": "alpha", "category": "animal", "split": "test"},
        {"word": "beta", "category": "object", "split": "test"},
    ]
    man = {"version": 1, "name": "syn", "words": words, "images": images, "screens": screens}
    vecs = np.zeros((6 * 22, DIM), dtype=np.float32)
    for s in (0, 1, 2):
        vecs[s * 22 + 0, 0] = 1
    vecs[4 * 22 + 0, 1] = 1
    vecs[5 * 22 + 0, 1] = 1
    vecs[5 * 22 + 1, 0] = 1  # false cover of alpha on a lookalike card
    regions = [
        {"regionId": f"r{k}", "rect": {"x": 0, "y": k * 250, "w": W, "h": H}} for k in range(3)
    ] + [{"regionId": f"r{k}", "rect": {"x": 0, "y": 770, "w": 5, "h": 5}} for k in range(3, 22)]
    d = tmp_path / "b"
    fmt.write_bench(d, man, vecs, regions)
    return fmt.load_bench(d)


def test_metrics_and_gate(bench):
    res = evaluate.evaluate_bench(bench, bench.manifest["words"], _cc_fn, _judge)
    a, b = res["words"]
    m = a["modes"]["balanced"]
    assert (m["recall"], m["precision"], m["cleanFalseCover"]) == (0.75, 0.75, 0.5)
    assert a["lookalikeFC"] == 0.5 and a["nPos"] == 4 and not a["passes"]
    assert a["classes"] == ["drawing", "lookalike"]
    mb = b["modes"]["balanced"]
    assert (mb["recall"], mb["precision"], mb["cleanFalseCover"]) == (1.0, 1.0, 0.0)
    assert b["passes"] and b["lookalikeFC"] is None
    assert res["passing"] == 1 and res["gateShare"] == 0.5
    assert res["categories"] == {"animal": 0.0, "object": 1.0}


def _cc_fn(word):
    return _cc(word)


def test_classify():
    assert evaluate.classify([{"small": True, "drawing": False}], [], False, True) == ["small"]
    assert evaluate.classify([], [{"lookalike": False}], True, False) == ["labels?"]
    assert evaluate.classify([], [], False, True) == ["other"]


def test_report(bench, tmp_path):
    res = evaluate.evaluate_bench(bench, bench.manifest["words"], _cc_fn, _judge)
    p = tmp_path / "r.md"
    evaluate.write_report(p, bench, res, [])
    t = p.read_text(encoding="utf-8")
    assert "Gate: FAIL" in t and "alpha" in t and "(c) narrow" in t


def test_attempts_exhausted(tmp_path):
    log = tmp_path / "a.jsonl"
    for k in range(1, 6):
        assert attempts.start("h", "bank", "p", "n", log) == k
        attempts.finish(k, 0.5, 1, log)
    with pytest.raises(attempts.Exhausted):
        attempts.start("h", "bank", "p", "n", log)
    assert len(attempts.read(log)) == 10


def test_dry_refused_on_v1():
    attempts.check_dry("mini", True)
    with pytest.raises(attempts.DryRefused):
        attempts.check_dry("v1", True)


def test_tamper_refused(bench, tmp_path):
    mp = bench.dir / "manifest.json"
    mp.write_bytes(mp.read_bytes().replace(b"alpha", b"alphb"))
    assert (
        evaluate.main(["--bench", str(bench.dir), "--bank", str(tmp_path), "--split", "dev"]) == 2
    )


def test_no_word_params():
    ws = word_params_check.words()
    assert "snake" in ws
    assert word_params_check.literal_hits(ws) == []
    assert word_params_check.module_hits(ws) == []
