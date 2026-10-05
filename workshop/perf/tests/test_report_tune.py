import shutil
from pathlib import Path

from workshop.perf import report, tune
from workshop.perf.schema import Row, Section


def _sec(name: str, ok: bool) -> Section:
    return Section(name, rows=[Row("AC-5.3-00", "m", 1.0, "t", ok)]).finish()


def test_report_gate(tmp_path: Path):
    ev = tmp_path / "ev"
    ev.mkdir()
    for n in ("latency", "smooth", "battery"):
        _sec(n, True).write(ev / f"{n}.json")
    out = tmp_path / "r.md"
    assert report.main(["--evidence", str(ev), "--out", str(out)]) == 0
    assert "Gate: PASS" in out.read_text("utf-8")
    _sec("battery", False).write(ev / "battery.json")
    report.main(["--evidence", str(ev), "--out", str(out)])
    assert "Gate: FAIL" in out.read_text("utf-8")


def test_report_empty(tmp_path: Path):
    (tmp_path / "ev").mkdir()
    out = tmp_path / "r.md"
    report.main(["--evidence", str(tmp_path / "ev"), "--out", str(out)])
    text = out.read_text("utf-8")
    assert "PENDING-HUMAN" in text and "Gate: PASS" not in text


def test_tune_sync(tmp_path: Path):
    twin, android = tmp_path / "a.json", tmp_path / "b.json"
    shutil.copy(tune.TWIN, twin)
    tune.apply([], twin, android)
    assert tune.in_sync(twin, android)
    tune.apply(["balanced.sched.rate=7"], twin, android)
    assert '"rate": 7' in android.read_text("utf-8") and tune.in_sync(twin, android)
    android.write_text("{}", encoding="utf-8")
    assert not tune.in_sync(twin, android)
    assert tune.in_sync()
