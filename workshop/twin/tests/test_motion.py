import json

import pytest

from workshop.replay.player import replay
from workshop.replay.tape import validate_file
from workshop.twin import cache, gatekeeper, goldens, planner, tracker
from workshop.twin.motion import MotionPipeline, run_tape
from workshop.twin.motion_synth import generate
from workshop.twin.oracle import OracleDetector, OracleParams
from workshop.twin.tests import motion_stubs

FULL = {"x": 0, "y": 0, "w": 720, "h": 1600}


@pytest.fixture(scope="module")
def video_run(tmp_path_factory):
    d = tmp_path_factory.mktemp("motion")
    sj = generate(d, "video", 6)
    pipe = MotionPipeline(sj, "balanced", use_cache=False)
    res = replay(sj, pipe, d / "out", self_capture=True, video=False)
    return sj, pipe, res


def test_real_modules_are_used():
    pipe = MotionPipeline(None, "balanced")
    assert isinstance(pipe.tracker, tracker.Tracker)
    assert isinstance(pipe.gk, gatekeeper.GatekeeperPipeline)
    assert isinstance(pipe.cache, cache.FingerprintCache)
    assert planner.plan and not isinstance(pipe.tracker, motion_stubs.StubTracker)


def test_real_detector_is_deferred():
    with pytest.raises(SystemExit, match="DEFERRED"):
        MotionPipeline(None, "balanced", detector="real")


def test_run_tape_equals_live(video_run):
    _, pipe, res = video_run
    recs = goldens.merge_tape_in(res.tape_in, pipe.findings_log)
    p = res.tape_in.parent / "merged.tape-in.jsonl"
    goldens._write(p, recs)
    assert validate_file(p) == []
    again = run_tape(p)
    live = goldens._strip(goldens._records(res.tape_out))
    assert goldens._strip(again) == live
    assert any(r["kind"] == "maskPlan" and r["plan"]["masks"] for r in again)


def test_findings_log_merge_order(video_run):
    _, pipe, res = video_run
    assert pipe.findings_log
    recs = goldens.merge_tape_in(res.tape_in, pipe.findings_log)
    assert [r["seq"] for r in recs] == list(range(len(recs)))
    for i, r in enumerate(recs):
        if r["kind"] == "finding":
            nxt = next(x for x in recs[i + 1 :] if x["kind"] != "finding")
            assert nxt["kind"] == "frame" and nxt["frameId"] == r["x"]["deliverFrameId"]


def test_oracle_is_deterministic_and_respects_own_covers(video_run):
    sj, _, _ = video_run
    sid = json.loads(sj.read_text())["sessionId"]
    det = OracleDetector(sj.parent / f"{sid}.truth.jsonl", p=OracleParams(seed=1, miss_pct=0))
    frame = {"frameId": 100, "tMs": 4000, "ownOverlay": []}
    a = det.detect(frame, FULL, 1)
    assert a == det.detect(frame, FULL, 1)
    assert a and a[0]["conceptId"] == "cats" and a[0]["layer"] == 2
    covered = {"frameId": 100, "tMs": 4000, "ownOverlay": [FULL]}
    assert [f for f in det.detect(covered, FULL, 1) if f["findingId"].endswith("-0")] == []


def test_a1_confirm_look_fires_when_idle_after_tentative():
    import numpy as np

    pipe = MotionPipeline(None, "balanced", use_cache=False)
    img = np.zeros((1600, 720, 3), dtype=np.uint8)

    def fr(t, fid):
        return {
            "tMs": t, "frameId": fid, "screenWidth": 720, "screenHeight": 1600,
            "width": 720, "height": 1600, "ownOverlay": [],
        }  # fmt: skip

    pipe.on_frame(img, fr(0, 1))
    pipe.tracker.on_findings(
        [
            {
                "findingId": "f",
                "conceptId": "cats",
                "layer": 2,
                "rect": {"x": 100, "y": 400, "w": 200, "h": 200},
                "decision": "hide",
            }
        ],
        900,
    )
    recs = pipe.on_frame(img, fr(1000, 2))
    look = next(r for r in recs if r["kind"] == "look")
    assert look["look"] and look["x"].get("confirm")
