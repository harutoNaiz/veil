import ast
from pathlib import Path

import numpy as np

from workshop.twin import change
from workshop.twin.change import ChangeParams, detect, shift_rows, thumb_box_to_screen

rng = np.random.default_rng(5)


def tex(seed):
    return np.random.default_rng(seed).integers(0, 200, (64, 32), dtype=np.uint8)


def test_static_and_blink():
    a = tex(1)
    r = detect(a, a, 0)
    assert r.changed_tiles == 0 and not r.scene_cut and r.score == 0
    b = a.copy()
    b[10:12, 10:12] = np.clip(b[10:12, 10:12].astype(int) + 120, 0, 255)
    assert detect(b, a, 0).changed_tiles == 0
    c = a.copy()
    c[:2] = 255
    c[62:] = 0
    assert detect(c, a, 0).changed_tiles == 0


def test_pure_scroll():
    ref = tex(2)
    cur = np.zeros_like(ref)
    cur[:-3] = ref[3:]
    cur[-3:] = tex(3)[-3:]
    r = detect(cur, ref, -3)
    assert r.revealed_rows == (59, 62)
    assert [i for i, s in enumerate(r.tile_scores) if s >= 12] == [28, 29, 30, 31]
    assert not r.scene_cut


def test_scene_cut_and_reels():
    assert detect(tex(4), tex(5), 0).scene_cut
    r = detect(tex(4), tex(5), -70)
    assert r.revealed_rows == (2, 62) and not r.scene_cut and r.changed_tiles == 32


def test_slow_fade():
    ref = (tex(6) // 6).astype(np.uint8)
    hits = [
        k for k in range(1, 30) if detect((ref + 7 * k).astype(np.uint8), ref, 0).changed_tiles > 0
    ]
    assert hits and not detect(ref, None, 0).scene_cut


def test_shift_and_box():
    assert shift_rows(25, 360, 800, 720) == 1
    assert shift_rows(-12, 360, 800, 720) == 0
    assert shift_rows(-13, 360, 800, 720) == -1
    assert shift_rows(-1600, 360, 800, 720) == -64
    f = {"width": 360, "height": 800, "screenWidth": 720}
    assert thumb_box_to_screen((0, 59, 32, 62), f) == {"x": 0, "y": 1475, "w": 720, "h": 75}


def test_integer_only():
    src = Path(change.__file__).read_text()
    tree = ast.parse(src)
    bad = {"float", "round", "mean", "sqrt", "math", "float32", "float64"}
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "thumb"]:
        tree.body.remove(fn)
    for n in ast.walk(tree):
        assert not isinstance(n, ast.Div)
        assert not (isinstance(n, ast.Constant) and isinstance(n.value, float))
        assert not (isinstance(n, ast.Name) and n.id in bad)
        assert not (isinstance(n, ast.Attribute) and n.attr in bad)
    r = detect(tex(7), tex(8), 0, ChangeParams())
    assert type(r.score) is int and type(r.scene_cut) is bool and type(r.changed_tiles) is int
    assert all(type(s) is int for s in r.tile_scores)
    assert r.changed_box is None or all(type(v) is int for v in r.changed_box)
