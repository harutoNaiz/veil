import json
from pathlib import Path

from workshop.perf.battery import session, stats

FIX = Path(__file__).parent / "fixtures"


def _runs() -> list[dict]:
    return json.loads((FIX / "runs.json").read_text("utf-8"))


def test_parsers():
    assert stats.parse_level((FIX / "battery_start.txt").read_text()) == 94
    assert stats.parse_level((FIX / "battery_end.txt").read_text()) == 88
    on = (FIX / "batterystats_on.txt").read_text()
    assert stats.parse_uid_mah(on, "com.veil.guard", "u0a123") == 18.75
    assert stats.parse_uid_mah((FIX / "batterystats_off.txt").read_text(), "com.veil.guard") is None
    assert stats.parse_uid("  userId=10123\n") == "u0a123"


def test_pass_section():
    runs = _runs()
    assert round(stats.extra_pct(runs), 1) == 10.0
    sec = stats.build_section(runs)
    assert sec.status == "PASS"
    assert len(stats.battery_table(runs)) == 7


def test_fail_extra():
    runs = _runs()
    for r in runs:
        if r["label"] in ("A-on", "B-on"):
            r["endLevel"] = 92
    sec = stats.build_section(runs)
    assert sec.status == "FAIL"  # 8 % vs 6 % = 33 % extra


def test_pending_and_conditions():
    assert stats.build_section(_runs()[:2]).status == "PENDING"
    runs = _runs()
    runs[1]["brightness"] = 200
    sec = stats.build_section(runs)
    assert sec.status == "FAIL" and "conditions differ" in sec.notes


def test_session_no_device(monkeypatch):
    monkeypatch.setattr("workshop.bench.adb.single_device", lambda: None)
    assert session.main(["--minutes", "0"]) == 2
