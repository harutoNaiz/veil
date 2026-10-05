import json

from workshop.guardcheck.cat_feed import check


def _logs(cover: dict | None):
    def item(i, kind, y):
        return {"itemId": i, "kind": kind, "rect": {"x": 0, "y": y, "w": 100, "h": 100}}

    vis = [item("a", "cat", 0), item("b", "clean", 200)]
    feed = "\n".join(
        json.dumps({"type": "frame", "tMs": t, "scrollY": 0, "visible": vis})
        for t in (1000, 1200, 1400, 1600)
    )
    masks = [{"rect": cover}] if cover else []
    debug = json.dumps({"kind": "plan", "tMs": 900, "masks": masks})
    return debug, feed


def test_pass():
    rep = check(*_logs({"x": 0, "y": 0, "w": 100, "h": 100}))
    assert rep.clean and rep.checked == 4, rep.problems


def test_fail_missed_cat_and_covered_clean():
    rep = check(*_logs(None))
    assert not rep.clean and any("cat" in p for p in rep.problems)
    rep = check(*_logs({"x": 0, "y": 0, "w": 100, "h": 300}))
    assert not rep.clean and any("clean" in p for p in rep.problems)
