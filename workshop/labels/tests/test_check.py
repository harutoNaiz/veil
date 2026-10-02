from __future__ import annotations

import copy

from workshop.labels import check

NAMES = ["instagram-explore-0001.png", "instagram-explore-0002.png"]
META = {
    "app": "instagram",
    "surface": "explore",
    "mode": "dark",
    "orientation": "portrait",
    "source": "synth",
}


def _clean(name):
    return {
        "contractVersion": "1.0",
        "image": name,
        "width": 360,
        "height": 780,
        "clean": True,
        "boxes": [],
        "meta": META,
    }


def test_ok_and_each_problem_kind(make_screens):
    screens = make_screens(NAMES)
    good = [_clean(n) for n in NAMES]
    assert check.check(good, screens) == []

    missing = check.check(good[:1], screens)
    assert missing == [f"{NAMES[1]}: no label entry"]

    wrong_size = copy.deepcopy(good)
    wrong_size[0]["width"] = 361
    assert "size 361x780 != PNG 360x780" in check.check(wrong_size, screens)[0]

    invalid = copy.deepcopy(good)
    invalid[1]["clean"] = False  # not clean but no boxes
    problems = check.check(invalid, screens)
    assert len(problems) == 1 and problems[0].startswith(f"{NAMES[1]}: invalid")

    no_meta = copy.deepcopy(good)
    del no_meta[0]["meta"]
    assert check.check(no_meta, screens) == [f"{NAMES[0]}: meta missing"]


def test_cli_exit_codes(make_screens, tmp_path, capsys):
    import json

    screens = make_screens(NAMES)
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps([_clean(n) for n in NAMES]), encoding="utf-8")
    assert check.main(["--labels", str(labels), "--screens", str(screens)]) == 0
    assert "LABELS OK 2" in capsys.readouterr().out
    labels.write_text(json.dumps([_clean(NAMES[0])]), encoding="utf-8")
    assert check.main(["--labels", str(labels), "--screens", str(screens)]) == 1
    assert check.main(["--labels", str(tmp_path / "nope.json"), "--screens", str(screens)]) == 2
