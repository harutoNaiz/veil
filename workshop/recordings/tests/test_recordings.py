import json
import shutil
import types

import cv2
import pytest

from workshop.contracts.validate import validate
from workshop.recordings import index, record, sync_check
from workshop.recordings.estimate import estimate_scroll
from workshop.recordings.synth_session import generate


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    d = tmp_path_factory.mktemp("synth")
    return d, generate(d)


def _load(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def test_session_files_and_events(session):
    d, path = session
    s = json.loads(path.read_text(encoding="utf-8"))
    assert s["frameCount"] == 600 and all(v >= 2 for v in s["situations"].values())
    cap = cv2.VideoCapture(str(d / s["video"]))
    assert (int(cap.get(3)), int(cap.get(4)), int(cap.get(7))) == (360, 800, 600)
    ev = _load(d / "synth-known-scroll.events.jsonl")
    for e in ev:
        validate("UiEvent", e)
    assert [e["eventId"] for e in ev] == list(range(len(ev)))
    assert [e["tMs"] for e in ev] == sorted(e["tMs"] for e in ev)
    label = json.loads((d / "labels" / "synth-known-scroll.json").read_text(encoding="utf-8"))
    assert label["tracks"] and {m["type"] for m in label["marks"]} >= {
        "sceneCut",
        "appSwitch",
        "lock",
        "unlock",
    }


def test_estimator_matches_truth(session):
    d, path = session
    s = json.loads(path.read_text(encoding="utf-8"))
    est = estimate_scroll(d / s["video"], 720, "com.veil.synth", fps=30, t0_ms=1000)
    got = {e["tMs"]: e["dy"] for e in est}
    drv = {
        x["tMs"]: x["dy"] for x in json.loads((d / "synth-known-scroll.driver.json").read_text())
    }
    ok = sum(
        1 for t, dy in drv.items() if t in got and abs(got[t] - dy) <= 2
    )  # +-1 frame px = 2 screen px
    assert ok >= 0.9 * len(drv)
    assert [t for t in got if t not in drv] == []  # no events in pauses


def test_sync_pass_and_fail(session, tmp_path):
    _, path = session
    assert sync_check.check(path)["pass"]
    generate(tmp_path, seconds=10, event_offset_ms=100)
    assert not sync_check.check(tmp_path / "synth-known-scroll.session.json")["pass"]


def test_record_with_fake_adb(session, tmp_path):
    d, _ = session
    sample = d / "synth-known-scroll.orig.mp4"
    calls = []

    def fake(cmd, **kw):
        if cmd[0] != "adb":
            return record._run(cmd)
        calls.append(cmd)
        out = ""
        if cmd[2:] == ["cat", "/proc/uptime"]:
            out = "5000.50 123.0\n"
        elif cmd[2:] == ["wm", "size"]:
            out = "Physical size: 720x1600\n"
        elif cmd[1] == "pull":
            shutil.copyfile(sample, cmd[3])
        return types.SimpleNamespace(stdout=out, returncode=0)

    p = record.record("rec1", 20, tmp_path, ["fling"], runner=fake)
    s = json.loads(p.read_text(encoding="utf-8"))
    assert s["t0Ms"] == 5000500 and s["scroll"] == "estimated" and s["source"] == "phone"
    assert any("screenrecord" in c for c in calls)
    assert (tmp_path / "rec1.events.jsonl").stat().st_size > 0


def test_index(session):
    d, _ = session
    idx = index.build(d)
    assert idx["totalSeconds"] == 20 and idx["situations"]["reelsSwipe"] == 4
    assert not idx["ac_2_1_01"] and not idx["ac_2_1_02"]


def test_label_validates(session):
    from workshop.labels.recordings import validate as validate_label

    d, _ = session
    label = json.loads((d / "labels" / "synth-known-scroll.json").read_text(encoding="utf-8"))
    assert validate_label(label) == []
    assert all(t["conceptId"] != "dogs" for t in label["tracks"])
