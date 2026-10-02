import hashlib
import json
from pathlib import Path

import cv2
import pytest

from workshop.replay import checks
from workshop.replay.pipeline import DummyPipeline
from workshop.replay.player import replay
from workshop.replay.tape import check_line, validate_file
from workshop.replay.tests.fixture import build

EXAMPLES = Path(__file__).resolve().parents[3] / "contracts" / "examples-tape"


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    return build(tmp_path_factory.mktemp("fx"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_event_before_frame_and_determinism(session, tmp_path):
    a = replay(session, DummyPipeline(), tmp_path / "a", video=False)
    b = replay(session, DummyPipeline(), tmp_path / "b", video=False)
    assert sha(a.tape_in) == sha(b.tape_in) and sha(a.tape_out) == sha(b.tape_out)
    recs = [json.loads(x) for x in a.tape_in.read_text().splitlines()]
    i = next(k for k, r in enumerate(recs) if r["kind"] == "event" and r["tMs"] == 2000)
    assert recs[i + 1]["kind"] == "frame" and recs[i + 1]["tMs"] == 2000


def test_self_capture_error(session):
    assert checks.self_capture_error(session, frames=60) <= 1


def test_tapes_validate_and_examples(session, tmp_path):
    r = replay(session, DummyPipeline(), tmp_path, video=False, self_capture=True)
    assert validate_file(r.tape_in) == [] and validate_file(r.tape_out) == []
    for f in sorted(EXAMPLES.glob("valid-*")):
        assert check_line(json.loads(f.read_text())) is None
    for f in sorted(EXAMPLES.glob("invalid-*")):
        assert check_line(json.loads(f.read_text())) is not None
    assert checks.scroll_totals(r.tape_in) == [-180]


def test_realtime_and_covered_video(session, tmp_path):
    r = replay(session, DummyPipeline(), tmp_path, realtime=True, video=False)
    t = json.loads(r.timing.read_text())
    assert t["wallS"] <= 3.5 and r.late_frames <= 0.05 * r.frames
    r = replay(session, DummyPipeline(), tmp_path / "v", markers=True)
    cap, n = cv2.VideoCapture(str(r.video)), 0
    while cap.read()[0]:
        n += 1
    assert n == 90
