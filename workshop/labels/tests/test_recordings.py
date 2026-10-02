import json
import shutil
from pathlib import Path

from workshop.labels import recordings as R

FIX = Path(__file__).parent / "fixtures"


def rect(x, y=0, w=100, h=100):
    return {"x": x, "y": y, "w": w, "h": h}


def make_label(sid="s", n=1, x0=0):
    tracks = [
        {
            "key": f"cat-{i}",
            "conceptId": "cats",
            "spans": [{"startMs": 1000, "endMs": 1400}],
            "keyframes": [
                {"tMs": 1000, "rect": rect(x0, i * 200)},
                {"tMs": 1400, "rect": rect(x0 + 40, i * 200)},
            ],
        }
        for i in range(n)
    ]
    return {
        "labelVersion": "1",
        "sessionId": sid,
        "durationMs": 3000,
        "screenWidth": 720,
        "screenHeight": 1600,
        "labeller": "t",
        "reviewedBy": None,
        "tracks": tracks,
        "marks": [{"tMs": 2000, "type": "sceneCut"}],
        "clean": [{"startMs": 2000, "endMs": 3000}],
    }


def test_valid_and_invalid():
    assert R.validate(make_label()) == []
    gap = make_label()
    gap["tracks"][0]["spans"][0]["endMs"] = 2000
    gap["tracks"][0]["keyframes"].append({"tMs": 2000, "rect": rect(0)})
    assert any("gap" in e for e in R.validate(gap))
    overlap = make_label()
    overlap["clean"] = [{"startMs": 1200, "endMs": 2500}]
    assert any("overlaps" in e for e in R.validate(overlap))
    extra = make_label()
    extra["bogus"] = 1
    assert R.validate(extra)


def test_boxes_at_interpolation():
    lab = make_label()
    assert R.boxes_at(lab, 1000)[0]["rect"]["x"] == 0
    assert R.boxes_at(lab, 1400)[0]["rect"]["x"] == 40
    assert R.boxes_at(lab, 1200)[0]["rect"]["x"] == 20
    assert R.boxes_at(lab, 1001)[0]["rect"]["x"] == 0
    assert R.boxes_at(lab, 2500) == []


def test_agree():
    a = make_label(n=10)
    assert R.agree(a, a) == 0.0
    b = make_label(n=10)
    b["tracks"][0]["keyframes"] = [
        {"tMs": 1000, "rect": rect(600)},
        {"tMs": 1400, "rect": rect(600)},
    ]
    # 1 of 10 boxes moved: 2 unmatched of 20 boxes.
    assert abs(R.agree(a, b) - 0.1) < 1e-9


def test_split_freeze(tmp_path):
    labels, recs = tmp_path / "l", tmp_path / "r"
    labels.mkdir()
    recs.mkdir()
    for i in range(6):
        sid = f"s{i}"
        (labels / f"{sid}.json").write_text(json.dumps(make_label(sid)), encoding="utf-8")
        (recs / f"{sid}.mp4").write_bytes(b"video" + bytes([i]))
        (recs / f"{sid}.events.jsonl").write_bytes(b"{}\n")
    split = R.split_freeze(labels, recs)
    assert len(split["dev"]) == 4 and len(split["test"]) == 2
    assert R.check_frozen(labels, recs)
    p = recs / f"{split['test'][0]}.mp4"
    p.write_bytes(p.read_bytes() + b"x")
    assert not R.check_frozen(labels, recs)


def test_from_ls(tmp_path):
    export = json.loads((FIX / "ls-video-export.json").read_text(encoding="utf-8-sig"))
    label = R.from_ls(export, FIX / "ls-video-session.json")
    assert R.validate(label) == []
    assert label["tracks"][0]["conceptId"] == "cats"
    assert label["marks"] == [{"tMs": 3000, "type": "sceneCut"}]
    assert R.boxes_at(label, 1000)[0]["rect"]["x"] == 72
    shutil.rmtree(tmp_path, ignore_errors=True)
