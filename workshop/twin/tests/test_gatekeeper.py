import base64
import json

import pytest

from workshop.replay.player import replay
from workshop.replay.tape import validate_file
from workshop.replay.tests.fixture import build
from workshop.twin import change
from workshop.twin import gatekeeper as gk
from workshop.twin.gatekeeper import GatekeeperPipeline, load_params, run_tape


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    d = tmp_path_factory.mktemp("gk")
    sj = build(d / "s")
    normal = replay(sj, GatekeeperPipeline("balanced"), d / "n", video=False)
    slow = replay(sj, GatekeeperPipeline("balanced", None, 500), d / "l", video=False)
    return normal, slow


def _lines(p):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]


def test_thumb_matches_tape(tmp_path):
    import cv2

    sj = build(tmp_path)
    r = replay(sj, GatekeeperPipeline("balanced"), tmp_path / "o", video=False)
    cap = cv2.VideoCapture(str(tmp_path / "fixture.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 5)
    _, img = cap.read()
    want = [x for x in _lines(r.tape_in) if x["kind"] == "frame"][5]["thumb"]
    assert base64.b64encode(change.thumb(img).tobytes()).decode() == want


def test_run_tape_equals_player(run):
    normal, _ = run
    out = [{k: v for k, v in r.items() if k != "seq"} for r in _lines(normal.tape_out)[1:]]
    assert run_tape(normal.tape_in, "balanced") == out


def test_tapes_validate(run):
    for r in run:
        assert validate_file(r.tape_in) == []
        assert validate_file(r.tape_out) == []


def test_slow_never_queues(run):
    _, slow = run
    recs = [r for r in _lines(slow.tape_out) if r["kind"] == "look"]
    ts = [r["tMs"] for r in recs if r["look"]]
    assert all(b - a >= 500 for a, b in zip(ts, ts[1:], strict=False))
    assert all(r["x"]["queue"] == 0 for r in recs)
    busy = sum(1 for r in recs if r["reason"] == "busy")
    assert busy == recs[-1]["x"]["skipped"] > 0


def test_params_roundtrip():
    p = load_params(gk.PARAMS)
    assert [p[m][1].rate for m in ("light", "balanced", "strict")] == [1, 3, 8]
    assert [p[m][1].checkup_ms for m in ("light", "balanced", "strict")] == [10000, 5000, 2000]
