import ast
import random
from pathlib import Path

from workshop.contracts.validate import validate
from workshop.twin.tracker import TRACK_MODES, Tracker, covered_pct, iou_pct


def R(x, y, w, h):
    return {"x": x, "y": y, "w": w, "h": h}


def F(rect, decision="hide", layer=2, concept="cats", fid="f1"):
    return {
        "findingId": fid,
        "conceptId": concept,
        "layer": layer,
        "rect": rect,
        "decision": decision,
    }


def test_two_pass_match():
    a = R(0, 0, 100, 100)
    assert iou_pct(a, R(53, 0, 100, 100)) == 30
    assert iou_pct(a, R(54, 0, 100, 100)) == 29
    tr = Tracker("strict")
    tr.on_findings([F(a)], 0)
    tr.on_findings([F(R(53, 0, 100, 100))], 10)
    assert len(tr.tick(10, [])) == 1
    tr2 = Tracker("strict")
    tr2.on_findings([F(a)], 0)
    tr2.on_findings([F(R(54, 0, 100, 100))], 10)
    assert len(tr2.tick(10, [])) == 2


def test_near_miss():
    assert iou_pct(R(0, 0, 100, 100), R(33, 0, 100, 100)) == 50
    assert iou_pct(R(0, 0, 100, 100), R(34, 0, 100, 100)) == 49
    tr = Tracker("balanced")
    tr.on_findings([F(R(0, 0, 100, 100))], 0)
    tr.on_findings([F(R(33, 0, 100, 100), "nearMiss")], 1000)
    d = tr.tick(1000, [])[0]
    assert d["sightings"] == 1 and d["holdUntilMs"] == 2500
    tr.on_findings([F(R(34, 0, 100, 100), "nearMiss")], 2000)
    assert tr.tick(2000, [])[0]["holdUntilMs"] == 2500
    tr3 = Tracker("balanced")
    tr3.on_findings([F(R(0, 0, 100, 100), "nearMiss")], 0)
    assert tr3.tick(0, []) == []


def test_tiebreak_lowest_id():
    tr = Tracker("balanced")
    tr.on_findings([F(R(0, 0, 100, 100), fid="a"), F(R(0, 60, 100, 100), fid="b")], 0)
    tr.on_findings([F(R(0, 30, 100, 100), fid="c")], 10)
    out = {d["trackId"]: d for d in tr.tick(10, [])}
    assert out[1]["sightings"] == 2 and out[2]["sightings"] == 1


def test_confirm_modes_and_layer1():
    for mode, n in (("light", 3), ("balanced", 2), ("strict", 1)):
        tr = Tracker(mode)
        for i in range(n):
            tr.on_findings([F(R(0, 0, 50, 50))], i * 10)
            state = tr.tick(i * 10, [])[0]["state"]
            assert state == ("confirmed" if i + 1 >= n else "tentative")
    tr = Tracker("light")
    tr.on_findings([F(R(0, 0, 50, 50), layer=1, concept="l1.x")], 0)
    assert tr.tick(0, [])[0]["state"] == "confirmed"


def test_scroll_exact():
    tr = Tracker("strict")
    tr.on_findings([F(R(10, 500, 50, 50))], 0)
    tr.on_scroll(-37, 5)
    assert tr.tick(5, [])[0]["rect"] == R(10, 463, 50, 50)


def test_hold_release():
    for mode, p in TRACK_MODES.items():
        tr = Tracker(mode)
        tr.on_findings([F(R(0, 0, 50, 50))], 0)
        assert len(tr.tick(p.hold_ms, [])) == 1
        assert tr.tick(p.hold_ms + 1, []) == []


def test_self_capture():
    for mode, p in TRACK_MODES.items():
        tr = Tracker(mode)
        tr.on_findings([F(R(0, 0, 100, 100))], 0)
        cover = [R(0, 0, 80, 100)]
        assert len(tr.tick(p.hold_ms + 1, cover)) == 1
        assert len(tr.tick(p.max_hold_ms - 1, cover)) == 1
        assert tr.tick(p.max_hold_ms, cover) == []
    tr = Tracker("balanced")
    tr.on_findings([F(R(0, 0, 100, 100))], 0)
    assert tr.tick(2000, [R(0, 0, 79, 100)]) == []
    tr = Tracker("balanced", self_capture_rule=False)
    tr.on_findings([F(R(0, 0, 100, 100))], 0)
    assert tr.tick(2000, [R(0, 0, 100, 100)]) == []
    tr = Tracker("balanced")
    tr.on_findings([F(R(0, 0, 100, 100))], 0)
    tr.on_scene_cut(1000)
    assert tr.tick(2000, [R(0, 0, 100, 100)]) == []
    assert covered_pct(R(0, 0, 10, 10), [R(0, 0, 10, 5), R(0, 3, 10, 5)]) == 80


def test_parked():
    tr = Tracker("balanced")
    tr.on_findings([F(R(0, 0, 100, 100))], 0)
    tr.on_findings([F(R(0, 0, 100, 100))], 10)
    tr.on_scroll(-1000, 20)
    d = tr.tick(100, [])[0]
    assert d["state"] == "parked" and d["parkedUntilMs"] == 3100
    tr.on_scroll(1000, 200)
    d = tr.tick(200, [])[0]
    assert d["state"] == "confirmed" and "parkedUntilMs" not in d
    tr.on_scroll(-1000, 300)
    tr.tick(300, [])
    assert tr.tick(3300, []) == []


def test_release_all_and_peek():
    tr = Tracker("strict")
    tr.on_findings([F(R(0, 0, 50, 50)), F(R(0, 300, 50, 50), layer=1, concept="l1.x")], 0)
    assert tr.peek(2, 1) is True
    assert tr.peek(1, 1) is False and tr.peek(9, 1) is False
    out = tr.tick(1, [])
    assert [d["peeked"] for d in out] == [False, True]
    for d in out:
        validate("Track", d)
    tr.on_app_change(2)
    assert tr.tick(2, []) == []
    tr.on_findings([F(R(0, 0, 50, 50))], 3)
    tr.on_screen_off(4)
    assert tr.tick(4, []) == []


def test_integer_only():
    src = Path(__file__).parents[1].joinpath("tracker.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    skip = {
        id(n)
        for f in ast.walk(tree)
        if isinstance(f, ast.FunctionDef) and f.name == "_fraction"
        for n in ast.walk(f)
    }
    for n in ast.walk(tree):
        if id(n) in skip:
            continue
        assert not isinstance(n, ast.Div)
        assert not (isinstance(n, ast.Constant) and isinstance(n.value, float))
        if isinstance(n, ast.Name):
            assert n.id not in ("float", "round", "math")
        if isinstance(n, ast.Import | ast.ImportFrom):
            assert "math" not in ast.dump(n)


def _run(seed):
    rng = random.Random(seed)
    tr = Tracker(rng.choice(list(TRACK_MODES)))
    log = []
    t = 0
    for _ in range(40):
        t += rng.randint(1, 900)
        op = rng.randint(0, 3)
        if op == 0:
            fs = [
                F(
                    R(
                        rng.randint(0, 600),
                        rng.randint(0, 1500),
                        rng.randint(20, 200),
                        rng.randint(20, 200),
                    ),
                    rng.choice(["hide", "hide", "nearMiss", "leave"]),
                    rng.choice([1, 2]),
                    rng.choice(["cats", "l1.x"]),
                    f"f{rng.randint(0, 99)}",
                )
                for _ in range(rng.randint(1, 4))
            ]
            tr.on_findings(fs, t)
        elif op == 1:
            tr.on_scroll(rng.randint(-400, 400), t)
        elif op == 2 and rng.randint(0, 9) == 0:
            tr.on_scene_cut(t)
        log.append(tr.tick(t, [R(rng.randint(0, 600), rng.randint(0, 1500), 150, 150)]))
    return log


def test_deterministic():
    for s in range(200):
        assert _run(s) == _run(s)
