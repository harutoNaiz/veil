import json

from workshop.forge import proof


def _f(x, y, w=10, h=10):
    return {"rect": {"x": x, "y": y, "w": w, "h": h}}


def test_decisions_and_compare(tmp_path):
    fa = {"cats": {"a.png": [_f(0, 0)], "b.png": []}, "dogs": {"a.png": []}}
    fb = {"cats": {"a.png": [_f(0, 0)], "b.png": [_f(5, 5)]}, "dogs": {"a.png": []}}
    da, db = proof.decisions(fa), proof.decisions(fb)
    assert da == {"a.png|cats": True, "b.png|cats": False, "a.png|dogs": False}
    res = proof.compare(
        {"decisions": da, "rects": proof._rects(fa)}, {"decisions": db, "rects": proof._rects(fb)}
    )
    assert res["same"] == 2 and res["differences"] == ["b.png|cats"] and not res["pass"]
    assert 0 < res["regionAgreement"] < 1


def test_write_compare(tmp_path):
    for n in ("a", "b"):
        (tmp_path / n).mkdir()
        s = {"decisions": {"x|cats": True}, "rects": {}}
        (tmp_path / n / "summary.json").write_text(json.dumps(s))
    res = proof.write_compare(tmp_path / "a", tmp_path / "b", tmp_path / "out")
    assert res["pass"] and (tmp_path / "out" / "diff.md").is_file()
