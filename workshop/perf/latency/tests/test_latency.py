from __future__ import annotations

import math

from workshop.perf.latency import parse
from workshop.perf.latency.tests.gen import make
from workshop.perf.schema import jsonl


def _run(tmp_path, **kw):
    make(tmp_path, **kw)
    debug, feed = jsonl(tmp_path / "debug.jsonl"), jsonl(tmp_path / "feedlog.jsonl")
    lat = parse.time_to_cover(parse.appearances(feed), debug)
    return lat, debug


def test_known_p95_passes(tmp_path):
    lat, debug = _run(tmp_path)
    assert len(lat) == 120
    assert parse.p95_ms(lat) == 213
    sec = parse.build_section(lat, parse.stage_breakdown(debug))
    assert sec.status == "PASS"


def test_slow_fixture_fails(tmp_path):
    lat, debug = _run(tmp_path, base=200, step=3)
    assert parse.p95_ms(lat) == 539
    assert parse.build_section(lat, parse.stage_breakdown(debug)).status == "FAIL"


def test_too_few_and_uncovered(tmp_path):
    lat, _ = _run(tmp_path, n=50)
    sec = parse.build_section(lat, {})
    assert sec.status == "FAIL" and any("50" in n for n in sec.notes)
    assert math.isinf(parse.p95_ms([{"latencyMs": None}] * 3))


def test_stage_breakdown_and_slowest(tmp_path):
    _, debug = _run(tmp_path)
    bd = parse.stage_breakdown(debug)
    assert bd["gate"]["p50"] == 10
    assert parse.slowest_stage(bd) in bd


def test_partial_cover_not_counted():
    apps = [("cat1", 0, [0, 0, 100, 100])]
    dbg = [{"kind": "plan", "tMs": 5, "lookId": 1, "masks": [{"rect": [0, 0, 50, 100]}]}]
    assert parse.time_to_cover(apps, dbg)[0]["latencyMs"] is None
