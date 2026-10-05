import json

from workshop.forge.cloud import precision


def _c(p, s, lat):
    return {"precision": p, "score": s, "latencyMs": lat}


def test_picks_w8a8_within_drop():
    cands = [_c("float16", 90, 3), _c("w8a16", 89.5, 2), _c("w8a8", 88.0, 1)]
    assert precision.choose(90, cands) == "w8a8"


def test_rejects_over_drop():
    cands = [_c("float16", 90, 3), _c("w8a16", 89.5, 2), _c("w8a8", 87.99, 1)]
    assert precision.choose(90, cands) == "w8a16"


def test_fallback_and_tie():
    assert precision.choose(90, [_c("w8a8", 80, 1)]) == "float16"
    assert precision.choose(90, [_c("w8a8", 90, 1), _c("float16", 90, 1)]) == "float16"


def test_fixture_run(tmp_path):
    assert precision.main(["--fixture", "--out", str(tmp_path)]) == 0
    d = json.loads((tmp_path / "precision.json").read_text())
    assert d["source"] == "fixture" and len(d["models"]) == 8
    for m in d["models"]:
        assert m["chosen"] in {c["precision"] for c in m["candidates"]}
        assert m["delta"] <= 2.0
