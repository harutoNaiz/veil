import ast
from pathlib import Path

from workshop.contracts.validate import validate
from workshop.twin import planner

W, H = 720, 1600


def trk(i, x, y, w, h, layer=2, state="confirmed", peeked=False, concept="cats", scope="object"):
    return {
        "trackId": i,
        "conceptId": concept,
        "layer": layer,
        "rect": {"x": x, "y": y, "w": w, "h": h},
        "state": state,
        "peeked": peeked,
        "scope": scope,
    }


def mk(tracks, **kw):
    p = planner.plan(tracks, t_ms=5, frame_id=3, screen_w=W, screen_h=H, **kw)
    validate("MaskPlan", p)
    return p


def test_only_confirmed_unpeeked_and_pad():
    p = mk(
        [
            trk(1, 100, 100, 200, 100),
            trk(2, 400, 400, 50, 50, state="tentative"),
            trk(3, 400, 800, 50, 50, peeked=True),
        ]
    )
    assert len(p["masks"]) == 1
    assert p["masks"][0]["rect"] == {"x": 94, "y": 94, "w": 212, "h": 112}
    assert planner.pad({"x": 0, "y": 0, "w": 200, "h": 100}, 10, W, H) == {
        "x": 0,
        "y": 0,
        "w": 210,
        "h": 110,
    }
    assert planner.pad({"x": 800, "y": 0, "w": 50, "h": 50}, 6, W, H) is None


def test_light_drop_and_layers():
    tr = [trk(1, 100, 100, 20, 40), trk(2, 300, 300, 20, 40, layer=1, concept="spiders")]
    p = mk(tr, mode="light")
    assert [m["layer"] for m in p["masks"]] == [1]
    ov = [
        trk(1, 100, 100, 100, 100),
        trk(2, 150, 150, 100, 100),
        trk(3, 160, 160, 100, 100, layer=1),
    ]
    p = mk(ov)
    assert [(m["layer"], m["trackIds"]) for m in p["masks"]] == [(1, [3]), (2, [1, 2])]


def _inside(r, m):
    return (
        m["x"] <= r["x"]
        and m["y"] <= r["y"]
        and m["x"] + m["w"] >= r["x"] + r["w"]
        and m["y"] + m["h"] >= r["y"] + r["h"]
    )


def test_cap_24_keeps_everything_covered():
    tr = [trk(i + 1, 20 + (i % 5) * 140, 20 + (i // 5) * 190, 60, 80) for i in range(40)]
    p = mk(tr)
    assert len(p["masks"]) == 24
    for t in tr:
        assert any(_inside(t["rect"], m["rect"]) for m in p["masks"])


def test_styles_labels_post_bounds():
    tr = [trk(1, 100, 100, 80, 80), trk(2, 400, 100, 80, 80, layer=1, concept="spiders")]
    for mode, st in (("light", "blur"), ("balanced", "blur"), ("strict", "solid")):
        m = {x["layer"]: x for x in mk(tr, mode=mode)["masks"]}
        assert m[1]["style"] == "solid" and m[1]["peekable"] is False
        assert m[2]["style"] == st and m[2]["peekable"] is True
    assert mk(tr, solid_only=True)["masks"][1]["style"] == "solid"
    assert mk(tr, labels=True)["masks"][1]["label"] == "Hidden · cats"
    pb = {"x": 50, "y": 50, "w": 600, "h": 500}
    p = mk([trk(1, 100, 100, 80, 80, scope="wholeElement")], post_bounds=[pb])
    assert p["masks"][0]["rect"]["w"] >= 600


def test_integer_only():
    tree = ast.parse(Path(planner.__file__).read_text(encoding="utf-8"))
    for n in ast.walk(tree):
        assert not isinstance(n, ast.Div)
        assert not (isinstance(n, ast.Constant) and isinstance(n.value, float))
        assert not (isinstance(n, ast.Name) and n.id in ("float", "round", "math"))
