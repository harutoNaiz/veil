import json

from workshop.eval import score_motion as sm

BOX = {"x": 100, "y": 100, "w": 200, "h": 200}


def _t(i):
    return 1000 + i * 1000 // 30


def _make(tmp_path, n, covered, visible=None, clean=None):
    """covered/visible: sets of frame indices; one box 'k' (cats)."""
    visible = set(range(n)) if visible is None else visible
    sess = {"sessionId": "s", "fps": 30, "screenWidth": 720, "screenHeight": 1600}
    (tmp_path / "s.session.json").write_text(json.dumps(sess))
    rows = []
    for i in range(n):
        boxes = [{"key": "k", "conceptId": "cats", "rect": BOX}] if i in visible else []
        rows.append({"i": i, "tMs": _t(i), "boxes": boxes})
    (tmp_path / "s.truth.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    out = tmp_path / "out.jsonl"
    with open(out, "w") as f:
        for i in range(n):
            masks = [{"rect": BOX, "trackIds": [1]}] if i in covered else []
            rec = {"kind": "maskPlan", "frameId": i, "tMs": _t(i), "plan": {"masks": masks}}
            f.write(json.dumps(rec) + "\n")
    label = {"clean": [{"startMs": _t(a), "endMs": _t(b)} for a, b in clean]} if clean else None
    return tmp_path / "s.session.json", out, label


def test_one_flicker_counted(tmp_path):
    sj, out, label = _make(tmp_path, 12, {0, 1, 2, 5, 6, 7, 8, 9, 10, 11})
    assert sm.score(sj, out, label)["flicker"] == 1
    assert [m["type"] for m in sm.marks(sj, out, label)] == ["flicker"]


def test_gap_of_1200ms_is_not_flicker(tmp_path):
    n = 50
    sj, out, label = _make(tmp_path, n, {0, 1} | set(range(38, n)))
    assert sm.score(sj, out, label)["flicker"] == 0


def test_never_covered_run_is_infinity(tmp_path):
    sj, out, label = _make(tmp_path, 10, set())
    r = sm.score(sj, out, label)
    assert r["ttc_p95_ms"] == sm.INF and r["coverage_pct"] == 0.0


def test_time_to_cover_and_late_mark(tmp_path):
    sj, out, label = _make(tmp_path, 20, set(range(12, 20)))
    r = sm.score(sj, out, label)
    assert r["ttc_p95_ms"] == 400 and r["appearances"] == 1
    assert [m["type"] for m in sm.marks(sj, out, label)] == ["late"]


def test_wrong_cover_counted_once(tmp_path):
    sj, out, label = _make(tmp_path, 12, {3, 4, 5, 6}, visible=set(), clean=[(0, 11)])
    r = sm.score(sj, out, label)
    assert r["wrong_covers"] == 1 and r["wrong_per_min"] > 0


def test_agree():
    m = [{"tMs": 1000, "session": "s", "type": "late"}]
    assert sm.agree(m, [{"tMs": 1400, "session": "s", "type": "late"}])[0]
    assert not sm.agree(m, [{"tMs": 1600, "session": "s", "type": "late"}])[0]
