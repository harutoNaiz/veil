from __future__ import annotations

import json
from pathlib import Path

from workshop.bench import capture_logs

FIX = Path(__file__).parent / "fixtures" / "capture"


def test_good_fixture_passes() -> None:
    r = capture_logs.analyse(FIX / "good")
    assert r["pass"], r["verdicts"]
    m = r["metrics"]
    assert m["idle_fps"] <= 1.0
    assert m["sizes_by_rotation"] == {"0": [360, 792], "90": [792, 360]}
    assert m["stop_to_awaiting_ms"] == [400, 700]
    assert m["resume_count"] == 2
    assert m["max_outstanding"] == 1
    assert m["memory_growth_pct"] < 5
    assert m["blind_frames_per_package"] == {"com.netflix.mediaclient": 2}
    assert r["verdicts"]["blind-netflix"] == "PASS"


def test_bad_fixture_fails() -> None:
    r = capture_logs.analyse(FIX / "bad")
    assert not r["pass"]
    v = r["verdicts"]
    assert v["AC-4.1-02"] == "FAIL"  # idle 3 fps
    assert v["outstanding"] == "FAIL"  # 2 outstanding
    assert v["AC-4.1-04"] == "FAIL"  # no awaiting state
    assert capture_logs.main([str(FIX / "bad")]) == 1


def test_cli_good_exit_zero(tmp_path: Path) -> None:
    out = tmp_path / "r.json"
    assert capture_logs.main([str(FIX / "good"), "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["pass"] is True
