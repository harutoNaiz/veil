from __future__ import annotations

import json
from pathlib import Path

from workshop.contracts.validate import validate
from workshop.labels import ls_convert

FIXTURE = Path(__file__).parent / "fixtures" / "ls-export-mini.json"
NAMES = ["instagram-explore-0001.png", "instagram-explore-0002.png", "youtube-home-0003.png"]
META = {
    "app": "instagram",
    "surface": "explore",
    "mode": "dark",
    "orientation": "portrait",
    "source": "synth",
}


def _label(name, boxes, lookalikes=(), clean=False):
    return {
        "contractVersion": "1.0",
        "image": name,
        "width": 360,
        "height": 780,
        "clean": clean,
        "boxes": boxes,
        "lookalikes": list(lookalikes),
        "meta": META,
        "labeller": "tester",
    }


def _box(x, y, w, h, concept="cats", kind="photo", scope="object", tag=None):
    box = {"rect": {"x": x, "y": y, "w": w, "h": h}, "concept": concept, "kind": kind}
    if tag:
        box["tag"] = tag
    box["scope"] = scope
    return box


def test_from_ls_mini_export_exact(make_screens):
    screens = make_screens(NAMES)
    export = json.loads(FIXTURE.read_text(encoding="utf-8"))
    got = ls_convert.from_ls(export, screens, "tester")
    expected = [
        _label(
            NAMES[0],
            [
                _box(36, 78, 180, 390, kind="cartoon", scope="wholeElement"),
                _box(180, 390, 36, 39, kind="emoji", tag="cat-emoji"),
            ],
            ["dog"],
        ),
        _label(NAMES[1], [], ["fox", "stuffed-toy"], clean=True),
        _label(
            NAMES[2],
            [
                _box(90, 156, 72, 78, concept="spiders"),
                _box(0, 0, 1, 1, concept="spiders", kind="sticker", tag="spider-emoji"),
            ],
        ),
    ]
    assert got == expected
    for label in got:
        validate("ScreenLabel", label)


def test_unlabelled_or_contradictory_exits_2(make_screens, tmp_path, capsys):
    screens = make_screens(NAMES)
    export = json.loads(FIXTURE.read_text(encoding="utf-8"))
    export[1]["annotations"][0]["result"] = []  # no boxes, clean not ticked
    export[0]["annotations"][0]["result"].append(  # boxes and clean ticked
        {
            "type": "choices",
            "from_name": "clean",
            "to_name": "image",
            "value": {"choices": ["clean"]},
        }
    )
    path = tmp_path / "export.json"
    path.write_text(json.dumps(export), encoding="utf-8")
    out = tmp_path / "labels.json"
    code = ls_convert.main(
        [
            "from-ls",
            "--export",
            str(path),
            "--screens",
            str(screens),
            "--labeller",
            "t",
            "--out",
            str(out),
        ]
    )
    err = capsys.readouterr().err
    assert code == 2 and not out.exists()
    assert NAMES[0] in err and NAMES[1] in err and "unlabelled or contradictory" in err


def test_round_trip_through_prelabels(make_screens, tmp_path):
    screens = make_screens(NAMES)
    labels = [
        _label(
            NAMES[0],
            [
                _box(37, 81, 123, 211, scope="wholeElement"),
                _box(5, 700, 21, 17, tag="cat-text", kind="text"),
            ],
            ["dog", "fox"],
        ),
        _label(NAMES[1], [], ["lion"], clean=True),
        _label(NAMES[2], [_box(300, 10, 59, 400, concept="spiders", kind="drawing")]),
    ]
    src = tmp_path / "truth.json"
    src.write_text(json.dumps(labels), encoding="utf-8")
    tasks_path = tmp_path / "tasks.json"
    out = tmp_path / "back.json"
    assert (
        ls_convert.main(
            [
                "to-ls",
                "--screens",
                str(screens),
                "--url-prefix",
                "/x/",
                "--prelabels",
                str(src),
                "--out",
                str(tasks_path),
            ]
        )
        == 0
    )
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    assert [t["data"]["image"] for t in tasks] == ["/x/" + n for n in NAMES]
    assert (
        ls_convert.main(
            [
                "from-ls",
                "--export",
                str(tasks_path),
                "--screens",
                str(screens),
                "--labeller",
                "tester",
                "--accept-predictions",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    back = json.loads(out.read_text(encoding="utf-8"))
    assert len(back) == len(labels)
    for a, b in zip(labels, back, strict=True):
        assert [a[k] for k in ("image", "clean", "lookalikes")] == [
            b[k] for k in ("image", "clean", "lookalikes")
        ]
        assert len(a["boxes"]) == len(b["boxes"])
        for x, y in zip(a["boxes"], b["boxes"], strict=True):
            assert {k: v for k, v in x.items() if k != "rect"} == {
                k: v for k, v in y.items() if k != "rect"
            }
            assert all(abs(x["rect"][k] - y["rect"][k]) <= 1 for k in "xywh")


def test_config_matches_constants():
    assert ls_convert.config_problems() == []


def test_findings_as_prelabels(make_screens):
    screens = make_screens(NAMES)
    finding = {
        "contractVersion": "1.0",
        "findingId": "f-1",
        "lookId": 0,
        "tMs": 0,
        "image": NAMES[0],
        "rect": {"x": 36, "y": 78, "w": 180, "h": 390},
        "conceptId": "cats",
        "layer": 2,
        "lane": "finder",
        "decision": "hide",
        "probability": 1.0,
        "scope": "wholeElement",
    }
    ignored = dict(finding, findingId="f-2", decision="leave")
    tasks = ls_convert.to_ls(screens, "/x/", [finding, ignored])
    assert "predictions" not in tasks[1]
    boxes, clean, _ = ls_convert.parse_result(
        tasks[0]["predictions"][0]["result"], (360, 780), NAMES[0], []
    )
    assert not clean
    assert boxes == [_box(36, 78, 180, 390, scope="wholeElement")]
